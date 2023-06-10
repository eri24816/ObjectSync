count = 0
def gen_id():
    global count
    count += 1
    return '0_'+str(count)
    
def set_id_count(new_count:int):
    global count
    count = new_count