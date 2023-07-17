from typing import Any

def camel_to_snake(name):
    return ''.join(['_'+c.lower() if c.isupper() else c for c in name]).lstrip('_')

def snake_to_camel(name):
    import re
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), name)


class NameSpace:
    '''
    To stop IDEs from complaining about dynamic attributes
    '''
    def __setattr__(self, *args, **kwargs) -> None:
        super().__setattr__(*args, **kwargs)
    def __getattr__(self, *args, **kwargs) -> Any:
        return super().__getattribute__(*args, **kwargs)