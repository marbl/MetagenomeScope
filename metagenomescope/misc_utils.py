from .errors import WeirdError


def verify_unique(objs, obj_type="IDs"):
    if len(set(objs)) < len(objs):
        raise WeirdError(f"Duplicate {obj_type}: {objs}")
