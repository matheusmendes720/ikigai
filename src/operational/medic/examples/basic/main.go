// Package main is a minimal SDK consumer example.
//
//	go run ./examples/basic
//
// It runs the health gate against ../packages/core (the PAV kernel in this
// monorepo) and prints a one-line summary.
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/life-oss/medic/pkg/medic/healthcheck"
)

func main() {
	target := "../packages/core"
	if len(os.Args) > 1 {
		target = os.Args[1]
	}
	chk, err := healthcheck.New(target)
	if err != nil {
		log.Fatal(err)
	}
	chk.Skip("coverage") // keep the example snappy
	rep, err := chk.Run(context.Background())
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("health: target=%s lang=%s score=%d ok=%v checks=%d\n",
		rep.Target, rep.Language, rep.Score, rep.OK, len(rep.Checks))
	for _, c := range rep.Checks {
		icon := "✓"
		switch c.Severity {
		case "warn":
			icon = "⚠"
		case "fail":
			icon = "✗"
		}
		fmt.Printf("  %s %-12s %s\n", icon, c.Name, c.Err)
	}
}
