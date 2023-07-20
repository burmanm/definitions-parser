package types

import (
	"fmt"
	"strconv"
)

type Metadata struct {
	Key         string
	BuilderType BuilderType // list, boolean, string, int => yaml rendering
	ValueType   ValueType
}

type ValueType int

const (
	StaticConstant ValueType = iota
	StringValue
	SuppressedValue
	TemplateValue
)

type BuilderType int

const (
	BooleanBuilder BuilderType = iota
	StringBuilder
	IntegerBuilder
)

// Output returns the JVM compatible output from the Metadata
func (m *Metadata) Output(value string) string {
	switch m.ValueType {
	case StaticConstant:
		// Has to be booleanType..
		if set, err := strconv.ParseBool(value); set && err != nil {
			return m.Key
		}
		return ""
	case StringValue:
		return fmt.Sprintf("%s=%s", m.Key, value)
	case SuppressedValue:
		return fmt.Sprintf("%s%s", m.Key, value)
	default:
		return ""
	}
}
