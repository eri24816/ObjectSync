count = 1
def gen_id():
    global count
    count += 1
    return '0_'+str(count)
    