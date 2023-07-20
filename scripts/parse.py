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

    def parse_file(self, filepath: str, serverType: str):
        file = Path(filepath)
        key_name = file.name[:file.name.index(serverType) - 1]
        map_name = self.generate_map_name(key_name)
        types_name = key_name.replace('-', '_')
        config_file = Path(file).read_text()
        input = ednloads(config_file)

        regexp_prefixes = []
        reverse_map = {}
        proper_map = {}
        ignored_list = []

        if isinstance(input, ImmutableDict):
            props = input.dict.get(Keyword("properties"))
            if isinstance(props, ImmutableDict):
                for k, v in props.dict.items():
                    values: ImmutableDict = v
                    # keyword: Keyword = k
                    edn_type = values.dict.get(Keyword('type'))

                    if edn_type == 'list':
                        # Collection types do not interest us in this reverse operation
                        ignored_list.append(k.name)
                        continue

                    static_constant = values.dict.get(Keyword('static_constant'))
                    constant_key = static_constant if static_constant is not None else values.dict.get(Keyword('constant'))
                    constant = values.dict.get(Keyword('constant'))

                    # -ea, -agentlib and other special debug params are not interesting in our environment at this point
                    if constant_key is not None and (constant_key.startswith('-D') or constant_key.startswith('-X')):
                        metaVal = {"name": k.name, "edn_type": edn_type, "suppress": False}

                        if static_constant is not None:
                            metaVal["static_constant"] = static_constant

                        if constant is not None:
                            metaVal["constant"] = constant

                        # try:
                        #     equality_operator_index = constant.index('=')
                        #     constant = constant[:equality_operator_index]
                        # except ValueError:
                        #     pass

                        if values.dict.get(Keyword('suppress-equal-sign')):
                            # Special values, such as Xmx, Xss, Xms etc
                            regexp_prefixes.append(F'^{constant}')
                            metaVal['suppress'] = True

                        proper_map[k.name] = metaVal
                        reverse_map[constant_key] = metaVal
                    else:
                        # Some of these options are no longer usable in 4.1 so they're ignored. We add manually some processing here to
                        # ensure the property is supported
                       ignored_list.append(k.name)

        for key in ignored_list:
            print(F'Ignored key: {key}')

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

            generated.write(F'var {map_name} = map[string]types.Metadata{{\n')
            for k, v in reverse_map.items():
                builder_type = self.get_builder_type(v['edn_type'])
                name = v['name']
                generated.write(F'"{k}": {{Key: "{name}", BuilderType: {builder_type}')
                generated.write('}, \n')
            generated.write('}\n')

            generated.write(F'var {map_name}Prefix = map[string]types.Metadata{{\n')
            for k, v in proper_map.items():
                builder_type = self.get_builder_type(v['edn_type'])
                constant = v.get('constant')
                static_constant = v.get('static_constant')
                name = static_constant if static_constant is not None else constant

                value_type = "types.StaticConstant" if static_constant is not None else "types.SuppressedValue" if v['suppress'] else "types.StringValue"
                generated.write(F'"{k}": {{Key: "{name}", BuilderType: {builder_type}, ValueType: {value_type} }},\n')

            # Add manual items
            generated.write(F'"garbage_collector": {{Key: "", BuilderType: types.StringBuilder, ValueType: types.TemplateValue }},\n')

            generated.write('}\n')
            generated.write(F"""
            const(
                {map_name}PrefixExp = \"""")
            generated.write('|'.join(regexp_prefixes))
            generated.write('"\n)')

        self._maps.append(key_name)

    def get_builder_type(self, edn_type: str) -> str:
        match edn_type:
            case 'string':
                builder_type = 'StringBuilder'
            case 'boolean':
                builder_type = 'BooleanBuilder'
            case 'int':
                builder_type = 'IntegerBuilder'
            case _:
                builder_type = 'None'
        return "types." + builder_type

    def generate_map_name(self, filename: str) -> str:
        types_name = filename.replace('-', '_')
        return ''.join(x for x in types_name.title() if not x == "_")

    def write_file_header(self, writer: TextIOWrapper):
            writer.write("""
            //go:build !ignore_autogenerated
            // +build !ignore_autogenerated
            // Code is generated with scripts/parse.py. DO NOT EDIT.
            package generated
            """)

    # def write_finder(self):
    #     with open(F'{self._target_dir}/finder_generated.go', 'w') as generated:
    #         self.write_file_header(generated)
    #         generated.write("""
    #         import(
    #                 "regexp"
    #                 "github.com/burmanm/definitions-parser/pkg/types"
    #         )

    #        """)

    #         generated.write("var regexps = map[string]*regexp.Regexp{")
    #         for name in self._maps:
    #             map_name = name.replace('-', '_')
    #             generated.write(F'"{name}": regexp.MustCompile({map_name}PrefixExp),')
    #         generated.write("}\n")
    #         generated.write("var optionsMap = map[string]map[string]types.Metadata{")
    #         for name in self._maps:
    #             map_name = name.replace('-', '_')
    #             generated.write(F'"{name}": {map_name},')
    #         generated.write("}\n")

    #         generated.write("""
    #         func MapFinder(propKey string) map[string]types.Metadata {
    #             return optionsMap[propKey]
    #         }
    #         """)

    #         generated.write("""
    #         func RegexpFinder(propKey string) *regexp.Regexp {
    #             return regexps[propKey]
    #         }
    #         """)

if __name__ == '__main__':
    gen = Generator()
    cass_definitions_dir = "../cass-config-definitions"
    if len(sys.argv) > 1:
        cass_definitions_dir = sys.argv[1]

    # gen.parse_file(F'{cass_definitions_dir}/resources/jvm11-server-options/dse/jvm11-server-options-dse-6.8.0.edn')
    # gen.parse_file(F'{cass_definitions_dir}/resources/jvm8-server-options/dse/jvm8-server-options-dse-6.8.0.edn')
    # gen.parse_file(F'{cass_definitions_dir}/resources/jvm-server-options/dse/jvm-server-options-dse-6.8.0.edn')

    gen.parse_file(F'{cass_definitions_dir}/resources/jvm11-server-options/cassandra/jvm11-server-options-cassandra-4.0.0.edn', 'cassandra')
    gen.parse_file(F'{cass_definitions_dir}/resources/jvm-server-options/cassandra/jvm-server-options-cassandra-4.0.0.edn', 'cassandra')
    # gen.write_finder()
