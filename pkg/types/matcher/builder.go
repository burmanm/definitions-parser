package matcher

import (
	"strings"

	"github.com/burmanm/definitions-parser/pkg/types"
	"github.com/burmanm/definitions-parser/pkg/types/generated"
)

type MetadataMatcher struct {
}

// Parser returns the YAML key + YAML value. If key is empty, add the string to the additional-jvm-options
// Returned values are key, value, default_value
func (m MetadataMatcher) Parser(optionsKey, input string) (string, string, string) {
	// We need to parse the input.. imagine:
	// -Xmx4G => metadata + value
	// -Djava.net.preferIPv4Stack=true => metadata + true
	found, meta, value := prefixParser(optionsKey, input)
	if found {
		return meta.Key, value, meta.DefaultValueString
	}

	// Split to value and key
	parts := strings.Split(input, "=")
	metaMap := generated.MapFinder(optionsKey)
	key := parts[0]

	if meta, found := metaMap[key]; found {
		if len(parts) < 2 && meta.BuilderType == "boolean" {
			// Existence implies inclusion
			return meta.Key, "True", meta.DefaultValueString
		} else if len(parts) < 2 {
			// Invalid input - validation issue?
			return meta.Key, "", meta.DefaultValueString
		}

		return meta.Key, parts[1], meta.DefaultValueString
	}

	// Key not found - validation issue?
	return "", "", ""
}

func prefixParser(optionsKey, input string) (bool, *types.Metadata, string) {
	metaMap := generated.MapFinder(optionsKey)
	prefixMatcher := generated.RegexpFinder(optionsKey)

	subParts := prefixMatcher.FindStringSubmatchIndex(input)
	if len(subParts) > 0 {
		mapKey := input[subParts[0]:subParts[1]]
		value := input[subParts[1]:]
		metaValue := metaMap[mapKey]

		return true, &metaValue, value
	}

	return false, nil, ""
}
