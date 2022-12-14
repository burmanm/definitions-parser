from cmath import exp
import sys
import os

from io import TextIOWrapper
from edn_format import ImmutableDict, Keyword, loads as ednloads, ImmutableList
from pathlib import Path


"""
Generate Go bindings from the cass-config-definitions..
"""
class Generator():
    _target_dir = 'pkg/types/generated'
    _maps = []

    def parse_file(self, filepath: str):
        file = Path(filepath)
        key_name = file.name[:file.name.index('dse') - 1]
        types_name = key_name.replace('-', '_')
        config_file = Path(file).read_text()
        input = ednloads(config_file)

        regexp_prefixes = []
        reverse_map = {}

        if isinstance(input, ImmutableDict):
            props = input.dict.get(Keyword("properties"))
            if isinstance(props, ImmutableDict):
                for k, v in props.dict.items():
                    values: ImmutableDict = v
                    # keyword: Keyword = k
                    edn_type = values.dict.get(Keyword('type'))

                    if edn_type == 'list':
                        # Collection types do not interest us in this reverse operation
                        continue

                    default_value = values.dict.get(Keyword('default_value'))

                    if edn_type == 'boolean':
                        default_value = str(default_value).lower()

                    static_constant = values.dict.get(Keyword('static_constant'))
                    constant = static_constant if static_constant is not None else values.dict.get(Keyword('constant'))

                    # -ea, -agentlib and other special debug params are not interesting in our environment at this point
                    if constant is not None and (constant.startswith('-D') or constant.startswith('-X')):
                        metaVal = {"name": k.name, "edn_type": edn_type, "default_value": default_value}

                        try: 
                            equality_operator_index = constant.index('=')
                            constant = constant[:equality_operator_index]
                        except ValueError:
                            pass

                        if values.dict.get(Keyword('suppress-equal-sign')):
                            # Special values, such as Xmx, Xss, Xms etc
                            regexp_prefixes.append(F'^{constant}')

                        reverse_map[constant] = metaVal


        try:
            os.mkdir(F'{self._target_dir}')
        except FileExistsError:
            pass

        with open(F'{self._target_dir}/{types_name}_generated.go', 'w') as generated:
            self.write_file_header(generated)

            generated.write("""
            import(
                    "github.com/burmanm/definitions-parser/pkg/types"
            )
            """)

            generated.write(F'var {types_name} = map[string]types.Metadata{{\n')
            for k, v in reverse_map.items():
                name = v['name']
                builderType = v['edn_type']
                generated.write(F'"{k}": {{Key: "{name}", BuilderType: "{builderType}"')
                default_value = v['default_value']
                if default_value is not None:
                    generated.write(F', DefaultValueString: "{default_value}"')
                generated.write('}, \n')
            generated.write('}\n')
            generated.write(F"""
            const(
                {types_name}PrefixExp = \"""")
            generated.write('|'.join(regexp_prefixes))
            generated.write('"\n)')

        self._maps.append(key_name)

    def write_file_header(self, writer: TextIOWrapper):
            writer.write("""
            //go:build !ignore_autogenerated
            // +build !ignore_autogenerated
            // Code is generated with scripts/parse.py. DO NOT EDIT.
            package generated
            """)

    def write_finder(self):
        with open(F'{self._target_dir}/finder_generated.go', 'w') as generated:
            self.write_file_header(generated)
            generated.write("""
            import(
                    "regexp"
                    "github.com/burmanm/definitions-parser/pkg/types"
            )
            """)

            generated.write("var regexps = map[string]*regexp.Regexp{")
            for name in self._maps:
                map_name = name.replace('-', '_')
                generated.write(F'"{name}": regexp.MustCompile({map_name}PrefixExp),')
            generated.write("}\n")
            generated.write("var optionsMap = map[string]map[string]types.Metadata{")
            for name in self._maps:
                map_name = name.replace('-', '_')
                generated.write(F'"{name}": {map_name},')
            generated.write("}\n")

            generated.write("""
            func MapFinder(propKey string) map[string]types.Metadata {
                return optionsMap[propKey]
            }
            """)

            generated.write("""
            func RegexpFinder(propKey string) *regexp.Regexp {
                return regexps[propKey]
            }
            """)

if __name__ == '__main__':
    gen = Generator()
    cass_definitions_dir = "../cass-config-definitions"
    if len(sys.argv) > 1:
        cass_definitions_dir = sys.argv[1]

    gen.parse_file(F'{cass_definitions_dir}/resources/jvm11-server-options/dse/jvm11-server-options-dse-6.8.0.edn')
    gen.parse_file(F'{cass_definitions_dir}/resources/jvm8-server-options/dse/jvm8-server-options-dse-6.8.0.edn')
    gen.parse_file(F'{cass_definitions_dir}/resources/jvm-server-options/dse/jvm-server-options-dse-6.8.0.edn')
    gen.write_finder()
