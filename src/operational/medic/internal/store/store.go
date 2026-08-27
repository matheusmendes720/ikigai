// Package store implements the local .medic/ persistence layer.
//
// Every medic invocation that produces state (review reports, captured frames,
// health reports, workflow state) writes into the target repo's .medic/
// directory. We never write into the source tree above .medic/.
package store

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Store wraps a directory handle and provides namespaced sub-dirs.
type Store struct {
	root string
	mu   sync.Mutex
}

// New creates a Store rooted at <target>/.medic. Idempotent.
func New(target string) (*Store, error) {
	if target == "" {
		return nil, errors.New("store: empty target")
	}
	abs, err := filepath.Abs(target)
	if err != nil {
		return nil, err
	}
	root := filepath.Join(abs, ".medic")
	if err := os.MkdirAll(root, 0o755); err != nil {
		return nil, fmt.Errorf("mkdir %s: %w", root, err)
	}
	return &Store{root: root}, nil
}

// Root returns the .medic directory path.
func (s *Store) Root() string { return s.root }

// Sub returns <root>/<parts...>, creating it.
func (s *Store) Sub(parts ...string) (string, error) {
	p := filepath.Join(append([]string{s.root}, parts...)...)
	if err := os.MkdirAll(p, 0o755); err != nil {
		return "", err
	}
	return p, nil
}

// WriteJSON marshals v as indented JSON into <root>/<rel>.
func (s *Store) WriteJSON(rel string, v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	full := filepath.Join(s.root, rel)
	if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(full, data, 0o644)
}

// ReadJSON unmarshals <root>/<rel> into v.
func (s *Store) ReadJSON(rel string, v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	data, err := os.ReadFile(filepath.Join(s.root, rel))
	if err != nil {
		return err
	}
	return json.Unmarshal(data, v)
}

// WriteFile writes raw bytes to <root>/<rel>.
func (s *Store) WriteFile(rel string, data []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	full := filepath.Join(s.root, rel)
	if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
		return err
	}
	return os.WriteFile(full, data, 0o644)
}

// ReadFile reads raw bytes from <root>/<rel>.
func (s *Store) ReadFile(rel string) ([]byte, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return os.ReadFile(filepath.Join(s.root, rel))
}

// Exists returns true if <root>/<rel> exists.
func (s *Store) Exists(rel string) bool {
	_, err := os.Stat(filepath.Join(s.root, rel))
	return err == nil
}

// Glob returns paths matching the pattern relative to root.
func (s *Store) Glob(pattern string) ([]string, error) {
	var out []string
	err := filepath.WalkDir(s.root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		rel, _ := filepath.Rel(s.root, path)
		ok, err := filepath.Match(pattern, rel)
		if err != nil {
			return err
		}
		if ok {
			out = append(out, path)
		}
		return nil
	})
	return out, err
}

// SnapshotDir makes a timestamped sub-dir like 2026-06-22_17-04-12.
func (s *Store) SnapshotDir(prefix string) (string, error) {
	ts := time.Now().Format("2006-01-02_15-04-05")
	return s.Sub(prefix, ts)
}
