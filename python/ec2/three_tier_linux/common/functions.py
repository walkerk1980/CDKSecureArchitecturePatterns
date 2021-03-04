def unpack_constants_dict(obj: object, constants_dict: dict):
    for newvar in constants_dict.keys():
        setattr(obj, newvar, constants_dict.get(newvar))