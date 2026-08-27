// Package main runs the example pr-review.yaml workflow programmatically.
//
//	go run ./examples/workflow ./examples/workflow/pr-review.yaml ../packages/core
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/life-oss/medic/pkg/medic/agentflow"
)

func main() {
	if len(os.Args) < 2 {
		log.Fatal("usage: workflow <yaml-file> [target]")
	}
	workflowPath := os.Args[1]
	target := "../packages/core"
	if len(os.Args) > 2 {
		target = os.Args[2]
	}

	eng, err := agentflow.NewEngine(target)
	if err != nil {
		log.Fatal(err)
	}
	eng.Verbose(true)

	w, err := eng.LoadFile(workflowPath)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("loaded workflow %q (%d steps)\n", w.Name, len(w.Steps))

	rep, err := eng.Run(context.Background(), w)
	if err != nil {
		log.Fatal(err)
	}
	out, _ := json.MarshalIndent(rep, "", "  ")
	fmt.Println(string(out))
}
