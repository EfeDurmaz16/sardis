.PHONY: build install clean test lint release snapshot

BINARY := sardis
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS := -ldflags "-s -w -X main.version=$(VERSION)"

build:
	go build $(LDFLAGS) -o bin/$(BINARY) .

install:
	go install $(LDFLAGS) .

clean:
	rm -rf bin/ dist/

test:
	go test ./...

lint:
	golangci-lint run ./...

# Build cross-platform release binaries (requires goreleaser)
release:
	goreleaser release --clean

# Build snapshot (no publish, for testing)
snapshot:
	goreleaser release --snapshot --clean
