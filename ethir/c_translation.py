import rbr_rule
import os
from timeit import default_timer as dtimer

'''
This module translate the RBR generated by EthIR to SACO RBR.
It receives a list with rbr_rule instances.
'''

global pattern
pattern = ["PUSH1",
                   "DUP2",
                   "PUSH1",
                   "AND",
                   "ISZERO",
                   "PUSH2",
                   "MUL",
                   "SUB",
                   "AND",
                   "PUSH1",
                   "SWAP1",
                   "DIV"]

global svcomp
svcomp = False

global exit_tag
exit_tag = 0

global init_loop
init_loop = 0

global end_loop
end_loop = 0

global end_function
end_function = 0


def rbr2c(rbr,execution,cname,scc,svc_labels):
    global svcomp
    svcomp = svc_labels

    begin = dtimer()
    heads = "\n"
    new_rules = []

    scc_unit = scc["unary"]
    scc_multiple = scc["multiple"]

#    scc_r = filter(lambda x: len(x)>1,scc_multiple)
#    scc_r = scc_r+scc_unit


    scc_unary_rules = compute_sccs_unary(rbr,scc_unit)
    scc_multiple_rules = compute_sccs_multiple(rbr,scc_multiple)
    
    for rules in rbr: #it contains list of two elemtns (jumps) or unitary lists (standard rule)
       
        if len(rules) == 2:
            head,new_rule = process_jumps(rules)
        else:
            head,new_rule = process_rule_c(rules[0])
                
        heads = heads+head
        new_rules.append(new_rule)
    
    write_init(rbr,execution,cname)
    write(heads,new_rules,execution,cname)

    init = initialize_global_variables(rbr)
    write_main(execution,cname,init)
    end = dtimer()
    print("C RBR: "+str(end-begin)+"s")


def compute_sccs_unary(rbr,scc_unit):
    global init_loop
    
    rules = {}
    heads = []
    
    l = len(rbr)
    i = 0
    while i < l:
        r = rbr[i]
        if len(r) == 2:
            rid = r[0].get_Id()
            if rid in scc_unit:
                part_jump = translate_jump_scc(r,scc_unit,init_loop)
                i =i+1
                rule_main = rbr[i][0]
                head, part_main = translate_block_scc(rule_main,init_loop)
                init_loop+=1
                rule = part_main+"\n"+part_jump+"}"
                rules[rid] = rule
                heads.append(head)
        else:
            rid = r[0].get_Id()
            if rid in scc_unit:
                head, part_main = translate_block_scc(r[0],init_loop)
                i+=1
                rule_jump = rbr[i]
                part_jump = translate_jump_scc(rule_jump,scc_unit,init_loop)
                init_loop+=1
                rule = part_main+"\n"+part_jump+"}"
                rules[rid] = rule
                heads.append(head)

        i=i+1

    return heads, rules

def translate_jump_scc(r,scc,id_loop):
    global init_loop

    jump1 = r[0]
    jump2 = r[1]

    instructions1 = jump1.get_instructions()
    instructions2 = jump2.get_instructions()

    call_if = filter_call(instructions1[0])
    call_else = filter_call(instructions2[0])

    if_id = get_called_block(call_if)

    if if_id in scc:
        guard = jump1.get_guard()
        cond = translate_conditions(guard)
        call_instr = call_else

    else:
        guard = jump2.get_guard()
        cond = translate_conditions(guard)
        call_instr = call_if
        
    label = "goto init_loop_"+str(id_loop)

    body = "\tif("+cond+"){\n"
    body = body+"\t\t"+label+"; }\n"
    body = body+"\t"+call_instr+";\n"

    return body

def translate_block_scc(rule,id_loop):
    stack_variables = get_input_variables(rule.get_index_invars())
    stack = map(lambda x: "int "+x,stack_variables)
    s_head = ", ".join(stack)

    head_c = "void " + rule.get_rule_name()+"("+s_head+");\n"
    head = "void " + rule.get_rule_name()+"("+s_head+"){\n"

    cont = rule.get_fresh_index()+1
    instructions = rule.get_instructions()
    has_string_pattern = rule.get_string_getter()
    new_instructions,variables = process_body_c(instructions,cont,has_string_pattern)
    
    variables_d = get_variables_to_be_declared(stack_variables,variables)
    var_declarations = "\n"+variables_d+"\n"
    
    #To delete skip instructions
    new_instructions = filter(lambda x: not(x.strip().startswith("nop(")) and x!=";",new_instructions)

    new_instructions = new_instructions[:-1] #To delete the call instructions. It is always the last one.
    new_instructions = map(lambda x: "\t"+x,new_instructions)
    body = "\n".join(new_instructions)

    init_loop_label = "  init_loop_"+str(id_loop)+":\n"
    if rule.has_invalid() and svcomp:
        label = get_error_svcomp_label()+";\n"
    else:
        label = ""
        
    rule_c = head+var_declarations+init_loop_label+body+label
    
    return head_c,rule_c

def compute_sccs_multiple(rbr,scc_unit):
    pass


def unbox_variable(var):
    open_pos = var.find("(")
    close_pos = var.find(")")
    if open_pos !=-1 and close_pos !=-1:
        new_var = var[:open_pos]+var[open_pos+1:close_pos]
    else:
        new_var = var
    return new_var

def check_declare_variable(var,variables):
    if var not in variables:
        variables.append(var)

def get_stack_variables(variables):
    stack_variables = filter(lambda x: x.startswith("s"),variables)
    idx_list = map(lambda x: int(x.strip()[1:]),stack_variables)
    sorted_idx = sorted(idx_list)
    rebuild_stack_variables = map(lambda x: "int s"+str(x)+";\n",sorted_idx)
    s_vars = "\t".join(rebuild_stack_variables)
    return s_vars

def get_rest_variables(variables):
    r_variables = filter(lambda x: not(x.startswith("s")),variables)
    sorted_variables = sorted(r_variables)
    rebuild_rvariables = map(lambda x: "int "+x+";\n",sorted_variables)
    r_vars = "\t".join(rebuild_rvariables)
    return r_vars
    
def get_variables_to_be_declared(stack_variables,variables):
    vd = []
    for v in variables:
        if v not in stack_variables:
            vd.append(v)

    s_vars = get_stack_variables(vd)
    r_vars = get_rest_variables(vd)
    
    return "\t"+s_vars+"\t"+r_vars
    
def get_input_variables(idx):
    in_vars = []
    for i in xrange(idx-1,-1,-1):
        var = "s"+str(i)
        in_vars.append(var)
    return in_vars

def translate_conditions(instr):

    if instr.startswith("gt"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[3:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" > "+var2
    elif instr.startswith("geq"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[4:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" >= "+var2
    elif instr.startswith("lt"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[3:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" < "+var2
    elif instr.startswith("leq"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[4:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" <= "+var2
    elif instr.startswith("eq"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[3:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" == "+var2
    elif instr.startswith("neq"):
        arg1 = instr.split(",")[0].strip()
        arg2 = instr.split(",")[1].strip()
        var1 = unbox_variable(arg1[4:])
        var2 = unbox_variable(arg2[:-1])
        instr = var1+" != "+var2
    else:
        instr = "Error in guard translation"

    return instr

def filter_call(call_instruction):
    block = call_instruction.strip()[5:-1].strip()
    pos_open = block.find("(")
    arguments = block[pos_open+1:-1]
    variables = arguments.split(",")
    s_vars = filter(lambda x: x.strip().startswith("s("),variables)
    s_vars = map(lambda x: unbox_variable(x.strip()),s_vars)
    
    s_string = ", ".join(s_vars)
    call = block[:pos_open]+"("+s_string+")"
    return call


def get_called_block(call_instruction):
    block = call_instruction.strip()[5:-1].strip()
    pos_open = block.find("(")
    block_id = block[:pos_open].strip()

    try:
        return int(block_id)

    except:
        return block_id


def process_jumps(rules):
    jump1 = rules[0]
    jump2 = rules[1]

    stack_variables = get_input_variables(jump1.get_index_invars())
    stack = map(lambda x: "int "+x,stack_variables)
    s_head = ", ".join(stack)

    head_c ="void " + jump1.get_rule_name()+"("+s_head+");\n"
    head = "void " + jump1.get_rule_name()+"("+s_head+"){\n"

    guard = jump1.get_guard()
    instructions1 = jump1.get_instructions()
    instructions2 = jump2.get_instructions()
    
    cond = translate_conditions(guard)

    call_if = filter_call(instructions1[0])
    call_else = filter_call(instructions2[0])

    body = "\tif("+cond+"){\n"
    body = body+"\t\t"+call_if+"; }\n"
    body = body+"\telse {\n"
    body = body+"\t\t"+call_else+"; }\n"
    end = "}\n"

    rule_c = head+body+end
    return head_c,rule_c

    
def process_rule_c(rule):
    stack_variables = get_input_variables(rule.get_index_invars())
    stack = map(lambda x: "int "+x,stack_variables)
    s_head = ", ".join(stack)

    head_c = "void " + rule.get_rule_name()+"("+s_head+");\n"
    head = "void " + rule.get_rule_name()+"("+s_head+"){\n"

    cont = rule.get_fresh_index()+1
    instructions = rule.get_instructions()
    has_string_pattern = rule.get_string_getter()
    new_instructions,variables = process_body_c(instructions,cont,has_string_pattern)
    
    variables_d = get_variables_to_be_declared(stack_variables,variables)
    var_declarations = "\n"+variables_d+"\n"
    
    #To delete skip instructions
    new_instructions = filter(lambda x: not(x.strip().startswith("nop(")) and x!=";",new_instructions)
    
    new_instructions = map(lambda x: "\t"+x,new_instructions)
    body = "\n".join(new_instructions)

    if rule.has_invalid() and svcomp:
        label = get_error_svcomp_label()+";\n"
    else:
        label = ""
        
    end ="\n}\n"
    rule_c = head+var_declarations+body+label+end
    
    return head_c,rule_c


def is_number(var):
    try:
        r = int(var)
        b = True
    except:
        r = -1
        b = False
        
    return b,r

def abstract_integer(var):
    b,r = is_number(var)
    new_var = ""
    
    if b and r>4294967296:
        new_var = "4294967296"

    elif b and r<=4294967296:
        new_var = str(r)
    else:
        new_var = var
        
    return new_var
        
def compute_string_pattern(new_instructions):
    nop_inst = map(lambda x: "nop("+x+")",pattern)
    new_instructions = new_instructions+nop_inst
    return new_instructions

def process_body_c(instructions,cont,has_string_pattern):
    new_instructions = []
    variables = []
    #    instructions = filter(lambda x: x!= "", instructions)
    idx_loop = 0
    len_ins = len(instructions)
    
    #for instr in instructions:
    while(idx_loop<len_ins):
        instr = instructions[idx_loop]

        if idx_loop == 8 and has_string_pattern:
            new_instructions = compute_string_pattern(new_instructions)
            idx_loop = idx_loop+26
        else:
            cont = process_instruction(instr,new_instructions,variables,cont)
            idx_loop = idx_loop+1

    new_instructions = filter(lambda x: x!= "", new_instructions)
    return new_instructions,variables


def process_instruction(instr,new_instructions,vars_to_declare,cont):        
    if instr.find("nop(")!=-1:
        new = instr
        
    elif instr.find("call(",0)!=-1:
        call_block = instr[5:-1].strip()
        pos_open = call_block.find("(")
        block = call_block[:pos_open]
        
        args = call_block[pos_open+1:-1]
        vars_aux = args.split(",")
        stack_variables = filter(lambda x: x.startswith("s("),vars_aux)
        variables = map(lambda x : unbox_variable(x.strip()),stack_variables)
        new_variables = ", ".join(variables)
        new = block+"("+new_variables+")"

    elif instr.find("and(",0)!=-1:
        elems = instr.split("= and")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")

        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = "+ var1 +" & "+var2

        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("or(",0)!=-1:
        elems = instr.split("= or")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")

        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = "+ var1 +" | "+var2
            
        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("not(",0)!=-1:
        elems = instr.split("= not")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg1 = elems[1].strip()[1:-1]
        var1 = unbox_variable(arg1)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = ~"+ var1

        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("xor(",0)!=-1:
        elems = instr.split("= xor")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")

        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        if svcomp:
            new = var0+" = "+ get_nondet_svcomp_label()
        else:
            new = var0+" = "+ var1 +" ^ "+var2

        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("gs(",0)!=-1:
        pos = instr.find("=")
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        arg1 = instr[pos+1:].strip()
        var1 = unbox_variable(arg1)
        
        new = var0 +" = "+ var1
        check_declare_variable(var0,vars_to_declare)
        
    # elif instr.find("gl =",0)!=-1:
    #     pos = instr.find("=")
    #     arg0 = instr[:pos].strip()
    #     var0 = unbox_variable(arg0)

    #     arg1 = instr[pos+1:].strip()
    #     var1 = unbox_variable(arg1)
        
    #     new = var0 +" = " var1

    elif instr.find("l(l")!=-1:
        pos_local = instr.find("l(l")
        pos_eq = instr.find("=")
        if pos_eq < pos_local: #it is in the right
            arg0 = instr[:pos_eq].strip()
            var0 = unbox_variable(arg0)
            
            arg1 = instr[pos_eq+1:].strip()
            var1_aux = unbox_variable(arg1)
            var1 = var1_aux[1:]
            new = var0+" = "+var1
        else:
            arg0 = instr[:pos_eq].strip()
            var0_aux = unbox_variable(arg0)
            var0 = var0_aux[1:]

            if instr[pos_eq+1:].strip().startswith("fresh("):
                if svcomp:
                    new = var0+" = "+get_nondet_svcomp_label()
                else:
                    new = var0+" = s"+str(cont)
                    check_declare_variable("s"+str(cont),vars_to_declare)
                    cont+=1
            else:
                arg1 = instr[pos_eq+1:].strip()
                var1 = unbox_variable(arg1)
                new = var0+" = "+var1
    
    elif instr.find("ls(",0)!=-1:
        pos = instr.find("=")
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        arg1 = instr[pos+1:].strip()
        var1 = unbox_variable(arg1)
        
        new = var0 +" = "+ var1
        check_declare_variable(var0,vars_to_declare)
        
    # elif instr.find("ll =",0)!=-1:
    #     pos = instr.find("=")
    #     new = "l("+instr[:pos].strip()+") "+instr[pos:]        

    elif instr.find("fresh",0)!=-1:
        pos = instr.find("=")
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = s"+str(cont)
            check_declare_variable("s"+str(cont),vars_to_declare)
            cont+=1
        
    elif instr.find("= eq(",0)!=-1:
        elems = instr.split("= eq")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")

        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+ var1 +" == "+var2
        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("= lt(",0)!=-1:
        elems = instr.split("= lt")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")
        
        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+ var1 +" < "+var2
        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("= gt(",0)!=-1:
        elems = instr.split("= gt")
        arg0 = elems[0].strip()
        var0 = unbox_variable(arg0)

        arg12_aux = elems[1].strip()[1:-1]
        arg12 = arg12_aux.split(",")

        arg1 = arg12[0].strip()
        var1 = unbox_variable(arg1)

        arg2 = arg12[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+ var1 +" > "+var2
        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("g(",0)!=-1:
        pos = instr.find("=",0)
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        arg1 = instr[pos+1:].strip()
        var1 = unbox_variable(arg1)

        new = var0+" = "+var1
        if var0.startswith("g"):
            check_declare_variable(var1,vars_to_declare)
        else:
            check_declare_variable(var0,vars_to_declare)
            
    elif instr.find("^",0)!=-1:
        pos = instr.find("=",0)
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = s"+str(cont)
            check_declare_variable("s"+str(cont),vars_to_declare)
            cont+=1

        
    elif instr.find("byte",0)!=-1: # upper bound-> 255
        pos = instr.find("=",0)
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = 255"

        check_declare_variable(var0,vars_to_declare)
        
    elif instr.find("sha",0)!=-1:
        pos = instr.find("=",0)
        arg0 = instr[:pos].strip()
        var0 = unbox_variable(arg0)

        if svcomp:
            new = var0+" = "+get_nondet_svcomp_label()
        else:
            new = var0+" = s"+str(cont)
            check_declare_variable("s"+str(cont),vars_to_declare)
            cont+=1
        
    elif instr.find("+")!=-1:
        elems = instr.split("+")
        arg01 = elems[0].split("=")
        arg0 = arg01[0].strip()
        var0 = unbox_variable(arg0)

        arg1 = arg01[1].strip()
        var1 = unbox_variable(arg1)

        arg2 = elems[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+var1+" + "+var2
        
    elif instr.find("-")!=-1:
        elems = instr.split("-")
        arg01 = elems[0].split("=")
        arg0 = arg01[0].strip()
        var0 = unbox_variable(arg0)

        arg1 = arg01[1].strip()
        var1 = unbox_variable(arg1)

        arg2 = elems[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+var1+" - "+var2

    elif instr.find("*")!=-1:
        elems = instr.split("*")
        arg01 = elems[0].split("=")
        arg0 = arg01[0].strip()
        var0 = unbox_variable(arg0)

        arg1 = arg01[1].strip()
        var1 = unbox_variable(arg1)

        arg2 = elems[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+var1+" * "+var2

    elif instr.find("/")!=-1:
        elems = instr.split("/")
        arg01 = elems[0].split("=")
        arg0 = arg01[0].strip()
        var0 = unbox_variable(arg0)

        arg1 = arg01[1].strip()
        var1 = unbox_variable(arg1)

        arg2 = elems[1].strip()
        var2 = unbox_variable(arg2)

        new = var0+" = "+var1+" / "+var2
                
    elif len(instr.split("=")) > 1:
        slices = instr.split("=")
        
        arg1 = slices[0].strip()
        arg2 = slices[1].strip()

        arg2 = abstract_integer(arg2)
        
        var1 = unbox_variable(arg1)
        var2 = unbox_variable(arg2)

        new = var1+" = "+var2
        check_declare_variable(var1,vars_to_declare)
        
    elif instr.find("skip")!=-1:
        new = ""
        
    else:
        new = instr
            
    new_instructions.append(new+";")
    return cont


def get_current_initloop():
    if init_loop == 0:
        return init_loop
    else:
        return init_loop-1

def get_current_endloop():
    if end_loop == 0:
        return end_loop
    else:
        return end_loop-1 

def get_nondet_svcomp_label():
    return "__VERIFIER_nondet_int()"

def get_error_svcomp_label():
    return "ERROR: __VERIFIER_error()"

def add_svcomp_labels():
    labels = "";
    labels = labels+"extern int __VERIFIER_nondet_int();\n"
    labels = labels + "extern void __VERIFIER_error();\n"

    return labels

def initialize_global_variables(rules):

    s = ""
    
    if(len(rules)>1):
        r = rules[1][0]
    else:
        r = rules[0][0]
            
    fields_id = r.get_global_arg()[::-1]
    bc_data = r.get_bc()
    locals_vars = sorted(r.get_args_local())[::-1]

    
    fields = map(lambda x: "\tg"+str(x)+" = __VERIFIER_nondet_int()",fields_id)
    l_vars = map(lambda x: "\tl"+str(x)+" = __VERIFIER_nondet_int()",locals_vars)
    bc = map(lambda x: "\t"+x+" = __VERIFIER_nondet_int()",bc_data)

    if fields != []:
        s = s+";\n".join(fields)+";\n"

    if l_vars != []:
        s = s+";\n".join(l_vars)+";\n"

    if bc != []:
        s = s+";\n".join(bc)+";\n"
        
    return s
        
def write_init(rules,execution,cname):
    s = "\n"

    if svcomp:
        s = add_svcomp_labels()
        s = s+"\n"
        
    if execution == None:
        name = "/tmp/costabs/rbr.c"
    elif cname == None:
        name = "/tmp/costabs/rbr"+str(execution)+".c"
    else:
        name = "/tmp/costabs/"+cname+".c"
    with open(name,"w") as f:
        if(len(rules)>1):
            r = rules[1][0]
        else:
            r = rules[0][0]
        fields_id = r.get_global_arg()[::-1]
        bc_data = r.get_bc()
        locals_vars = sorted(r.get_args_local())[::-1]
                                
        fields = map(lambda x: "int g"+str(x),fields_id)
        l_vars = map(lambda x: "int l"+str(x),locals_vars)
        bc = map(lambda x: "int "+x,bc_data)
        
        
        if fields != []:
            s = s+";\n".join(fields)+";\n"

        if l_vars != []:
            s = s+";\n".join(l_vars)+";\n"

        if bc != []:
            s = s+";\n".join(bc)+";\n"
        
        f.write(s)
        
    f.close()

def write_main(execution,cname,init):
    if execution == None:
        name = "/tmp/costabs/rbr.c"
    elif cname == None:
        name = "/tmp/costabs/rbr"+str(execution)+".c"
    else:
        name = "/tmp/costabs/"+cname+".c"

    with open(name,"a") as f:
        
        s = "\nint main(){\n"
        if svcomp :
            s = s+"\n"+init+"\n"
        s = s+"\tblock0();\n"
        s = s+"\treturn 0;\n}"
        f.write(s)
    f.close()

def write(head,rules,execution,cname):
    
    # if "costabs" not in os.listdir("/tmp/"):
    #     os.mkdir("/tmp/costabs/")

    if execution == None:
        name = "/tmp/costabs/rbr.c"
    elif cname == None:
        name = "/tmp/costabs/rbr"+str(execution)+".c"
    else:
        name = "/tmp/costabs/"+cname+".c"
    with open(name,"a") as f:
        f.write(head+"\n")
        
        for rule in rules:
            f.write(rule+"\n")

    f.close()
