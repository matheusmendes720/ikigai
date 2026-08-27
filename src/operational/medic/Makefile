SHELL := pwsh.exe
BIN   := bin/medic$(EXE)
PKG   := ./...

.PHONY: all build run test test-race lint vet tidy clean install ui-action \
        demo seed golden review health dashboard debug visualize patterns \
        workflow-run workflow-list

all: vet test build

build:
	@mkdir -p bin
	go build -trimpath -ldflags "-s -w" -o $(BIN) ./cmd/medic

run: build
	./$(BIN)

test:
	go test -count=1 -timeout 90s $(PKG)

test-race:
	go test -race -count=1 -timeout 120s $(PKG)

lint:
	golangci-lint run ./...

vet:
	go vet $(PKG)

tidy:
	go mod tidy

clean:
	rm -rf bin coverage.out dist

install: build
	go install ./cmd/medic

demo:
	./$(BIN) demo seed

golden:
	./$(BIN) demo seed --dataset golden

review:
	./$(BIN) review --target .

health:
	./$(BIN) health --target .

dashboard:
	./$(BIN) dashboard --target .

debug:
	./$(BIN) debug --help

visualize:
	./$(BIN) visualize --help

patterns:
	./$(BIN) patterns --help

workflow-run:
	./$(BIN) workflow run examples/workflow/pr-review.yaml

workflow-list:
	./$(BIN) workflow list

ui-action:
	./$(BIN) ui action --help
