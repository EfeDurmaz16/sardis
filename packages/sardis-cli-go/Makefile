.PHONY: build install clean test

BINARY := sardis
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS := -ldflags "-s -w -X main.version=$(VERSION)"

build:
	go build $(LDFLAGS) -o bin/$(BINARY) .

install:
	go install $(LDFLAGS) .

clean:
	rm -rf bin/

test:
	go test ./...

lint:
	golangci-lint run ./...
