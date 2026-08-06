.PHONY: build test lint install clean

BIN_EXT := $(if $(filter windows,$(shell go env GOOS)),.exe,)

build:
	go build -o bin/printify2-pp-cli$(BIN_EXT) ./cmd/printify2-pp-cli

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/printify2-pp-cli

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/printify2-pp-mcp$(BIN_EXT) ./cmd/printify2-pp-mcp

install-mcp:
	go install ./cmd/printify2-pp-mcp

build-all: build build-mcp
