// Package medic is the public, stable surface of the medic toolkit.
//
// It is a thin re-export layer over the internal packages. Anything you can
// do via the `medic` CLI, you can do programmatically here.
//
// Quickstart:
//
//	import (
//	    "github.com/life-oss/medic/pkg/medic/reviewer"
//	    "github.com/life-oss/medic/pkg/medic/healthcheck"
//	    "github.com/life-oss/medic/pkg/medic/visualdebug"
//	)
//
//	r, _ := reviewer.New("life-oss/life", os.Getenv("GITHUB_TOKEN"))
//	rep, _ := r.ReviewPR(ctx, 142, "./packages/core")
//
//	h := healthcheck.New()
//	hRep, _ := h.Run(ctx, "./packages/core")
//
//	v := visualdebug.New(visualdebug.Options{Binary: "../apps/tui/bin/pav"})
//	v.Run(ctx, "scripts/demo.yaml", ".medic/visualize")
//
// The sub-packages are versioned independently of the internal/* packages:
// API-breaking changes will follow semver.
package medic
