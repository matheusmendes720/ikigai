package visual

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// RecordingMeta is the small JSON document stored as meta.json inside
// every Recording. It captures the context under which the recording
// was made so reviewers can replay / diff / annotate later.
type RecordingMeta struct {
	Binary   string            `json:"binary"`
	Args     []string          `json:"args"`
	Cols     int               `json:"cols"`
	Rows     int               `json:"rows"`
	Cwd      string            `json:"cwd,omitempty"`
	Env      map[string]string `json:"env,omitempty"`
	Term     string            `json:"term,omitempty"`
	Script   string            `json:"script,omitempty"`
	Started  time.Time         `json:"started"`
	Duration time.Duration     `json:"duration_ns"`
	Frames   int               `json:"frames"`
	Tags     []string          `json:"tags,omitempty"`
}

// TimelineEntry describes one frame in timeline.json.
// Index is 0-based; Offset is the wall-clock time since Started.
type TimelineEntry struct {
	Index    int           `json:"index"`
	Offset   time.Duration `json:"offset_ns"`
	Hash     string        `json:"hash"`
	Size     int           `json:"size"`
	Captured time.Time     `json:"captured"`
}

// Recording is the on-disk artefact produced by Recorder. It is a
// directory containing frames/NNN.{txt,svg}, timeline.json, and meta.json.
//
// Recording implements io.Closer so callers can defer r.Close() to flush
// pending state.
type Recording struct {
	Dir       string         `json:"dir"`
	Meta      RecordingMeta  `json:"meta"`
	Timeline  []TimelineEntry `json:"timeline"`
	mu        sync.Mutex
	framesDir string
	closed    bool
}

// Close flushes timeline.json and meta.json to disk. Safe to call twice.
// Errors from os.WriteFile are returned; subsequent Close calls return nil.
func (r *Recording) Close() error {
	if r == nil {
		return nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.closed {
		return nil
	}
	r.closed = true
	if err := r.flushLocked(); err != nil {
		return err
	}
	return nil
}

// Path returns the on-disk path to a specific frame file (without dir).
// Useful when you want to point a viewer at frame 7: recording.Path(7)+".svg".
func (r *Recording) Path(index int) string {
	return filepath.Join("frames", fmt.Sprintf("%06d", index))
}

// flushLocked writes the current Timeline and Meta to disk. Caller holds mu.
func (r *Recording) flushLocked() error {
	tlBytes, err := json.MarshalIndent(struct {
		Timeline []TimelineEntry `json:"timeline"`
		Meta     RecordingMeta   `json:"meta"`
	}{r.Timeline, r.Meta}, "", "  ")
	if err != nil {
		return err
	}
	tlPath := filepath.Join(r.Dir, "timeline.json")
	if err := os.WriteFile(tlPath, tlBytes, 0o644); err != nil {
		return err
	}
	metaBytes, err := json.MarshalIndent(r.Meta, "", "  ")
	if err != nil {
		return err
	}
	metaPath := filepath.Join(r.Dir, "meta.json")
	return os.WriteFile(metaPath, metaBytes, 0o644)
}

// Recorder captures frames to disk one at a time. Typical use:
//
//	rec := visual.NewRecorder()
//	if err := rec.Start(target); err != nil { ... }
//	for f := range frames {
//	    rec.Record(f)
//	}
//	rec.Stop()
//
// Recorder buffers per-frame writes but flushes meta/timeline at Stop().
// Concurrent Record calls are serialised.
type Recorder struct {
	rec     *Recording
	mu      sync.Mutex
	started time.Time
}

// NewRecorder returns a fresh, unstarted Recorder.
func NewRecorder() *Recorder { return &Recorder{}}

// Start prepares targetDir for a recording. Existing files are preserved
// unless they conflict with new frame names; in that case the new write
// wins and a warning is logged via the returned meta.Errors.
//
// targetDir is created if missing. Returns a snapshot Recording handle
// that can be inspected while the recording is in progress.
func (rec *Recorder) Start(targetDir string) (*Recording, error) {
	if targetDir == "" {
		return nil, fmt.Errorf("visual: recorder: empty target dir")
	}
	if err := os.MkdirAll(filepath.Join(targetDir, "frames"), 0o755); err != nil {
		return nil, fmt.Errorf("visual: recorder: mkdir: %w", err)
	}
	rec.mu.Lock()
	defer rec.mu.Unlock()
	now := time.Now()
	rec.started = now
	rec.rec = &Recording{
		Dir:       targetDir,
		Meta:      RecordingMeta{Started: now},
		Timeline:  nil,
		framesDir: filepath.Join(targetDir, "frames"),
	}
	return rec.rec, nil
}

// Record writes frame to the recording. The first non-nil frame sets the
// canonical Cols/Rows; subsequent frames of different size still write
// but are flagged in Meta via the Size field of the timeline entry.
func (rec *Recorder) Record(frame *Frame) error {
	if frame == nil {
		return fmt.Errorf("visual: recorder: nil frame")
	}
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if rec.rec == nil {
		return fmt.Errorf("visual: recorder: not started")
	}
	idx := len(rec.rec.Timeline)
	txtName := fmt.Sprintf("%06d.txt", idx)
	svgName := fmt.Sprintf("%06d.svg", idx)

	txtPath := filepath.Join(rec.rec.framesDir, txtName)
	svgPath := filepath.Join(rec.rec.framesDir, svgName)

	if err := os.WriteFile(txtPath, RenderTSV(frame), 0o644); err != nil {
		return fmt.Errorf("visual: recorder: write txt: %w", err)
	}
	if err := os.WriteFile(svgPath, RenderSVG(frame), 0o644); err != nil {
		return fmt.Errorf("visual: recorder: write svg: %w", err)
	}
	if rec.rec.Meta.Cols == 0 {
		rec.rec.Meta.Cols = frame.Cols
	}
	if rec.rec.Meta.Rows == 0 {
		rec.rec.Meta.Rows = frame.Rows
	}
	rec.rec.Timeline = append(rec.rec.Timeline, TimelineEntry{
		Index:    idx,
		Offset:   time.Since(rec.started),
		Hash:     frame.Hash,
		Size:     len(frame.Cells),
		Captured: frame.CapturedAt,
	})
	rec.rec.Meta.Frames = idx + 1
	rec.rec.Meta.Duration = time.Since(rec.started)
	return nil
}

// SetMeta mutates the recording's metadata. Safe to call before Stop();
// the values land on disk when Close is invoked.
func (rec *Recorder) SetMeta(meta RecordingMeta) {
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if rec.rec == nil {
		return
	}
	meta.Started = rec.rec.Meta.Started
	meta.Frames = rec.rec.Meta.Frames
	meta.Duration = rec.rec.Meta.Duration
	rec.rec.Meta = meta
}

// Stop flushes the recording and returns it. After Stop, the Recorder
// can be reused with another Start.
func (rec *Recorder) Stop() (*Recording, error) {
	rec.mu.Lock()
	defer rec.mu.Unlock()
	if rec.rec == nil {
		return nil, fmt.Errorf("visual: recorder: not started")
	}
	rec.rec.Meta.Duration = time.Since(rec.started)
	if err := rec.rec.Close(); err != nil {
		return rec.rec, err
	}
	out := rec.rec
	rec.rec = nil
	return out, nil
}

// LoadRecording reads a previously-saved Recording from disk.
//
// The returned Recording has Meta, Timeline, and Dir populated, but the
// frames themselves are not eagerly loaded — call Frame(index) to read
// one back.
func LoadRecording(dir string) (*Recording, error) {
	metaPath := filepath.Join(dir, "meta.json")
	metaBytes, err := os.ReadFile(metaPath)
	if err != nil {
		return nil, fmt.Errorf("visual: load meta: %w", err)
	}
	var meta RecordingMeta
	if err := json.Unmarshal(metaBytes, &meta); err != nil {
		return nil, fmt.Errorf("visual: parse meta: %w", err)
	}
	tlPath := filepath.Join(dir, "timeline.json")
	tlBytes, err := os.ReadFile(tlPath)
	if err != nil {
		return nil, fmt.Errorf("visual: load timeline: %w", err)
	}
	var tlWrap struct {
		Timeline []TimelineEntry `json:"timeline"`
		Meta     RecordingMeta   `json:"meta"`
	}
	if err := json.Unmarshal(tlBytes, &tlWrap); err != nil {
		return nil, fmt.Errorf("visual: parse timeline: %w", err)
	}
	r := &Recording{
		Dir:       dir,
		Meta:      meta,
		Timeline:  tlWrap.Timeline,
		framesDir: filepath.Join(dir, "frames"),
	}
	return r, nil
}

// Frame reads a single frame back from disk. The .txt variant is used;
// SVG would work but is much larger.
func (r *Recording) Frame(index int) (*Frame, error) {
	if r == nil {
		return nil, fmt.Errorf("visual: nil recording")
	}
	if index < 0 || index >= len(r.Timeline) {
		return nil, fmt.Errorf("visual: frame %d out of range", index)
	}
	txt := filepath.Join(r.framesDir, fmt.Sprintf("%06d.txt", index))
	return readFrameFile(txt)
}

// Frames returns all frames in order. Use sparingly on long recordings;
// for large diffs prefer lazy Frame(i) calls.
func (r *Recording) Frames() ([]*Frame, error) {
	if r == nil {
		return nil, fmt.Errorf("visual: nil recording")
	}
	out := make([]*Frame, 0, len(r.Timeline))
	for i := range r.Timeline {
		f, err := r.Frame(i)
		if err != nil {
			return out, err
		}
		out = append(out, f)
	}
	return out, nil
}

// DiffAgainst compares r frame-by-frame against otherDir (another
// recording) and returns a FrameSetDiff. See CompareFrameSets for
// pairing rules.
func (r *Recording) DiffAgainst(otherDir string) (*FrameSetDiff, error) {
	if r == nil {
		return nil, fmt.Errorf("visual: nil recording")
	}
	return CompareFrameSets(r.framesDir, otherDir)
}

// ListFrameFiles returns the on-disk paths of all frames sorted by index.
// Useful for piping into `medic golden update` style commands.
func (r *Recording) ListFrameFiles() ([]string, error) {
	if r == nil {
		return nil, fmt.Errorf("visual: nil recording")
	}
	entries, err := os.ReadDir(r.framesDir)
	if err != nil {
		return nil, err
	}
	var paths []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if !strings.HasSuffix(e.Name(), ".txt") {
			continue
		}
		paths = append(paths, filepath.Join(r.framesDir, e.Name()))
	}
	sort.Strings(paths)
	return paths, nil
}

// Recording implements io.Closer; ensure we satisfy it at compile time.
var _ io.Closer = (*Recording)(nil)