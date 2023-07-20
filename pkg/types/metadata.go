package types

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
