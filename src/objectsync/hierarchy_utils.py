from typing import TYPE_CHECKING, List


if TYPE_CHECKING:
    from objectsync.sobject import SObject

def get_ancestors(obj:'SObject') -> List['SObject']:
    '''
    Returns a list of all ancestors of obj, including itself, starting with the root
    '''
    ancestors = []
    while not obj.is_root():
        ancestors.append(obj)
        obj = obj.get_parent()
    ancestors.append(obj)
    ancestors.reverse()
    return ancestors

def lowest_common_ancestor(objs:List['SObject']) -> 'SObject':
    '''
    Returns the lowest common ancestor of two objects
    '''

    # traverse up the tree from obj1
    all_ancestors = []
    min_len = 10000
    for obj in objs:
        ancestors = get_ancestors(obj)
        all_ancestors.append(ancestors)
        min_len = min(min_len,len(ancestors))

    # find the lowest common ancestor
    
    for i in range(min_len):
        for j in range(len(all_ancestors)):
            if all_ancestors[j][i] != all_ancestors[0][i]:
                return all_ancestors[j][i-1]
    return all_ancestors[0][min_len-1]