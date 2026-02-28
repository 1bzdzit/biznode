import requests

def check_verification(config):
    mode = config.get("mode", "local")

    if mode == "local":
        return "UNVERIFIED"

    if mode == "registry":
        try:
            slug = config.get("entity_slug")
            api = config.get("registry_api")
            r = requests.get(f"{api}?entity={slug}", timeout=5)
            data = r.json()
            return data.get("status", "UNVERIFIED")
        except:
            return "UNVERIFIED"

    return "UNVERIFIED"