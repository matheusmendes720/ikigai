// Package main demonstrates the public medic.vision SDK.
//
// It builds a small synthetic TUI frame in memory, runs the
// MiniMax-VL-01 critique on it, and prints the parsed findings.
//
// Run:
//
//	go run ./examples/vision_critic
//
// If mmx or MINIMAX_API_KEY is not available, the demo degrades to
// a dry-run that renders the synthetic frame as SVG so you can still
// inspect what the critic *would* see.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/life-oss/medic/examples/vision_critic/sample"
	"github.com/life-oss/medic/pkg/medic/vision"
)

func main() {
	if err := vision.Available(); err != nil {
		fmt.Printf("⚠ vision critic not available: %v\n", err)
		fmt.Println("→ to enable: scripts/install_mmx.sh && export MINIMAX_API_KEY=***")
		fmt.Println("→ falling back to dry-run (renders the synthetic frame).")
		dryRun()
		return
	}

	frame := sample.Frame()
	c := vision.New()
	cr, err := c.Critique(context.Background(), frame,
		vision.ComposeOpts(
			vision.WithTimeout(90*time.Second),
			vision.WithSize(120, 40),
		),
	)
	if err != nil {
		log.Fatalf("critique: %v", err)
	}
	fmt.Println(cr.String())
	out, _ := json.MarshalIndent(cr, "", "  ")
	if err := os.MkdirAll(".medic/vision", 0o755); err == nil {
		_ = os.WriteFile(".medic/vision/demo.json", out, 0o644)
		fmt.Println("saved → .medic/vision/demo.json")
	}
}

// dryRun renders the synthetic frame to SVG and writes a summary so
// the demo still produces an artefact even without mmx.
func dryRun() {
	frame := sample.Frame()
	svg := sample.RenderSVG(frame)
	if err := os.MkdirAll(".medic/vision", 0o755); err == nil {
		if err := os.WriteFile(".medic/vision/demo.svg", svg, 0o644); err == nil {
			fmt.Println("saved → .medic/vision/demo.svg")
		}
	}
	fmt.Println("(dry-run; no findings produced)")
}
