package store

import (
	"os"
	"path/filepath"
	"testing"
)

func TestStoreRoundtrip(t *testing.T) {
	dir := t.TempDir()
	s, err := New(dir)
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	if s.Root() != filepath.Join(dir, ".medic") {
		t.Errorf("Root() = %q, want %q", s.Root(), filepath.Join(dir, ".medic"))
	}
	payload := map[string]any{"a": 1, "b": "two"}
	if err := s.WriteJSON("sub/test.json", payload); err != nil {
		t.Fatalf("WriteJSON: %v", err)
	}
	var out map[string]any
	if err := s.ReadJSON("sub/test.json", &out); err != nil {
		t.Fatalf("ReadJSON: %v", err)
	}
	if out["a"].(float64) != 1 || out["b"].(string) != "two" {
		t.Errorf("roundtrip mismatch: %+v", out)
	}
	if !s.Exists("sub/test.json") {
		t.Errorf("Exists returned false for just-written file")
	}
}

func TestStoreSnapshotDir(t *testing.T) {
	dir := t.TempDir()
	s, _ := New(dir)
	sd, err := s.SnapshotDir("visualize")
	if err != nil {
		t.Fatalf("SnapshotDir: %v", err)
	}
	if !filepath.HasPrefix(sd, s.Root()) {
		t.Errorf("SnapshotDir outside root: %s", sd)
	}
	if _, err := os.Stat(sd); err != nil {
		t.Errorf("SnapshotDir not created: %v", err)
	}
}
