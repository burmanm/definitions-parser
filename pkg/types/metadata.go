package types

// Lifted some rendering rules from
// https://github.com/datastax/cass-config-definitions/blob/735ea79958e0942cf9d35d6dd8cc0df26c91a228/README.md
type Metadata struct {
	// omitEmpty bool // static_constant vs constant
	Key                string
	BuilderType        string // list, boolean, string, int => yaml rendering
	DefaultValueString string
	// DefaultValueInt    int
	// DefaultValueBool   bool
}
