"""JSON to Dart class conversion logic."""


class JsonToDartConverter:

    @staticmethod
    def _capitalize(s: str) -> str:
        return s[0].upper() + s[1:] if s else ""

    @staticmethod
    def _camel_case(s: str) -> str:
        parts = s.replace("-", "_").replace(".", "_").split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    @classmethod
    def generate_freezed_class(cls, class_name: str, data: dict) -> str:
        sub_classes = []
        fields = []

        for key, val in data.items():
            field_name = cls._camel_case(key)
            if isinstance(val, bool):
                dart_type = "bool?"
            elif isinstance(val, int):
                dart_type = "int?"
            elif isinstance(val, float):
                dart_type = "double?"
            elif isinstance(val, str):
                dart_type = "String?"
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], dict):
                    item_class_name = cls._capitalize(field_name) + "Item"
                    dart_type = f"List<{item_class_name}>?"
                    sub_classes.append(
                        cls.generate_freezed_class(item_class_name, val[0])
                    )
                else:
                    item_type = (
                        type(val[0]).__name__ if len(val) > 0 else "dynamic"
                    )
                    item_type = {
                        "str": "String",
                        "int": "int",
                        "float": "double",
                        "bool": "bool",
                    }.get(item_type, "dynamic")
                    dart_type = f"List<{item_type}>?"
            elif isinstance(val, dict):
                nested_class_name = cls._capitalize(field_name)
                dart_type = f"{nested_class_name}?"
                sub_classes.append(
                    cls.generate_freezed_class(nested_class_name, val)
                )
            else:
                dart_type = "dynamic"

            fields.append(f"    {dart_type} {field_name},")

        fields_str = "\n".join(fields)
        file_snake_case = class_name.lower()

        code = f"""import 'package:freezed_annotation/freezed_annotation.dart';

part '{file_snake_case}.freezed.dart';
part '{file_snake_case}.g.dart';

@freezed
class {class_name} with _${class_name} {{
  const factory {class_name}({{
{fields_str}
  }}) = _{class_name};

  factory {class_name}.fromJson(Map<String, dynamic> json) => _${class_name}FromJson(json);
}}"""
        if sub_classes:
            code += "\n\n" + "\n\n".join(sub_classes)
        return code

    @classmethod
    def generate_standard_class(
        cls,
        class_name: str,
        data: dict,
        is_optional: bool = True,
        gen_copy_with: bool = False,
        gen_equatable: bool = False,
    ) -> str:
        sub_classes = []
        fields = []
        constructor_args = []
        from_json_fields = []
        to_json_fields = []
        copy_with_args = []
        copy_with_assignments = []
        equatable_props = []

        nullable = "?" if is_optional else ""

        for key, val in data.items():
            field_name = cls._camel_case(key)
            equatable_props.append(field_name)

            if isinstance(val, bool):
                dart_type = "bool"
                from_json = (
                    f"json['{key}'] as bool?"
                    if is_optional
                    else f"json['{key}'] as bool"
                )
            elif isinstance(val, int):
                dart_type = "int"
                from_json = (
                    f"json['{key}'] as int?"
                    if is_optional
                    else f"json['{key}'] as int"
                )
            elif isinstance(val, float):
                dart_type = "double"
                from_json = (
                    f"(json['{key}'] as num?)?.toDouble()"
                    if is_optional
                    else f"(json['{key}'] as num).toDouble()"
                )
            elif isinstance(val, str):
                dart_type = "String"
                from_json = (
                    f"json['{key}'] as String?"
                    if is_optional
                    else f"json['{key}'] as String"
                )
            elif isinstance(val, list):
                if len(val) > 0 and isinstance(val[0], dict):
                    item_class_name = cls._capitalize(field_name) + "Item"
                    dart_type = f"List<{item_class_name}>"
                    sub_classes.append(
                        cls.generate_standard_class(
                            item_class_name,
                            val[0],
                            is_optional,
                            gen_copy_with,
                            gen_equatable,
                        )
                    )
                    from_json = (
                        f"(json['{key}'] as List<dynamic>?)?.map((e) => "
                        f"{item_class_name}.fromJson(e as Map<String, dynamic>)).toList()"
                    )
                else:
                    item_type = (
                        type(val[0]).__name__ if len(val) > 0 else "dynamic"
                    )
                    item_type = {
                        "str": "String",
                        "int": "int",
                        "float": "double",
                        "bool": "bool",
                    }.get(item_type, "dynamic")
                    dart_type = f"List<{item_type}>"
                    from_json = f"(json['{key}'] as List<dynamic>?)?.map((e) => e as {item_type}).toList()"
            elif isinstance(val, dict):
                nested_class_name = cls._capitalize(field_name)
                dart_type = nested_class_name
                sub_classes.append(
                    cls.generate_standard_class(
                        nested_class_name,
                        val,
                        is_optional,
                        gen_copy_with,
                        gen_equatable,
                    )
                )
                from_json = f"json['{key}'] != null ? {nested_class_name}.fromJson(json['{key}'] as Map<String, dynamic>) : null"
            else:
                dart_type = "dynamic"
                from_json = f"json['{key}']"

            fields.append(f"  final {dart_type}{nullable} {field_name};")

            if is_optional:
                constructor_args.append(f"    this.{field_name},")
            else:
                constructor_args.append(f"    required this.{field_name},")

            from_json_fields.append(f"      {field_name}: {from_json},")
            to_json = (
                f"'{key}': {field_name}?.toJson(),"
                if isinstance(val, dict)
                else (
                    f"'{key}': {field_name}?.map((e) => e.toJson()).toList(),"
                    if isinstance(val, list)
                    and len(val) > 0
                    and isinstance(val[0], dict)
                    else f"'{key}': {field_name},"
                )
            )
            to_json_fields.append(f"      {to_json}")

            copy_with_args.append(f"    {dart_type}? {field_name},")
            copy_with_assignments.append(
                f"      {field_name}: {field_name} ?? this.{field_name},"
            )

        fields_str = "\n".join(fields)
        args_str = "\n".join(constructor_args)
        from_json_str = "\n".join(from_json_fields)
        to_json_str = "\n".join(to_json_fields)

        copy_with_str = ""
        if gen_copy_with:
            cw_args = "\n".join(copy_with_args)
            cw_assign = "\n".join(copy_with_assignments)
            copy_with_str = f"""\n\n  {class_name} copyWith({{\n{cw_args}\n  }}) {{\n    return {class_name}(\n{cw_assign}\n    );\n  }}"""

        extends_clause = " extends Equatable" if gen_equatable else ""
        equatable_override = ""
        imports = (
            "import 'package:equatable/equatable.dart';\n\n"
            if gen_equatable
            else ""
        )
        if gen_equatable:
            props = ", ".join(equatable_props)
            equatable_override = f"""\n\n  @override\n  List<Object?> get props => [{props}];"""

        dart_code = f"""{imports}class {class_name}{extends_clause} {{
{fields_str}

  {class_name}({{
{args_str}
  }});

  factory {class_name}.fromJson(Map<String, dynamic> json) {{
    return {class_name}(
{from_json_str}
    );
  }}

  Map<String, dynamic> toJson() {{
    return {{
{to_json_str}
    }};
  }}{copy_with_str}{equatable_override}
}}"""
        if sub_classes:
            dart_code += "\n\n" + "\n\n".join(sub_classes)

        return dart_code