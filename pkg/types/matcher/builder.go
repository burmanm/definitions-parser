package matcher

import (
	"regexp"
	"strconv"
	"strings"

	"github.com/burmanm/definitions-parser/pkg/types"
	"github.com/burmanm/definitions-parser/pkg/types/generated"
)

type MetadataMatcher struct {
	metaMap       map[string]types.Metadata
	prefixMatcher *regexp.Regexp
}

func filenameToEdnKey(filename string) string {
	// EDN definitions are named with "-options" instead of filename ".options"
	return strings.ReplaceAll(filename, ".", "-")
}

func NewMetadataMatcher(filename string) *MetadataMatcher {
	optionsKey := filenameToEdnKey(filename)
	return &MetadataMatcher{
		metaMap:       generated.MapFinder(optionsKey),
		prefixMatcher: generated.RegexpFinder(optionsKey),
	}
}

// Parser returns the YAML key + YAML value. If key is empty, add the string to the additional-jvm-options
// Returned values are key, value, default_value
func (m *MetadataMatcher) Parse(input string) (string, string, string) {
	// We need to parse the input.. imagine:
	// -Xmx4G => metadata + value
	// -Djava.net.preferIPv4Stack=true => metadata + true
	found, meta, value := m.prefixParser(input)
	if found {
		return meta.Key, value, meta.DefaultValueString
	}

	// Split to value and key
	parts := strings.Split(input, "=")
	key := parts[0]

	if meta, found := m.metaMap[key]; found {
		if len(parts) < 2 && meta.BuilderType == "boolean" {
			// Existence implies inclusion
			return meta.Key, "true", meta.DefaultValueString
		} else if len(parts) < 2 {
			// Invalid input - validation issue?
			return meta.Key, "", meta.DefaultValueString
		}

		val := parts[1]
		if meta.BuilderType == "boolean" {
			boolVal, err := strconv.ParseBool(val)
			if err != nil {
				// Validation issue?
				return "", "", ""
			}
			val = strconv.FormatBool(boolVal)
		}
		return meta.Key, val, meta.DefaultValueString
	}

	// Key not found - validation issue?
	return "", "", ""
}

func (m *MetadataMatcher) prefixParser(input string) (bool, *types.Metadata, string) {
	subParts := m.prefixMatcher.FindStringSubmatchIndex(input)
	if len(subParts) > 0 {
		mapKey := input[subParts[0]:subParts[1]]
		value := input[subParts[1]:]
		metaValue := m.metaMap[mapKey]

		return true, &metaValue, value
	}

	return false, nil, ""
}
