package main

import "github.com/sardis-sh/sardis/packages/sardis-cli-go/cmd"

var version = "dev"

func main() {
	cmd.SetVersion(version)
	cmd.Execute()
}
