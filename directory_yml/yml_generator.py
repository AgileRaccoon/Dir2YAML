import yaml

def generate_yaml(structure_data, project_name):
    """
    structure_data: collect_directory_structures() の結果 (リスト)
    project_name:   自動生成 or ユーザ設定のプロジェクト名
    """
    root_data = {
        "project": {
            "name": project_name,
            "structure": structure_data
        }
    }
    return yaml.dump(
        root_data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        indent=2
    )
