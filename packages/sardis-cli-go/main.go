package main

import "github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/cmd"

var version = "dev"

func main() {
	cmd.SetVersion(version)
	cmd.Execute()
}
