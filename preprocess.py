def cwd():
    import os
    return os.getcwd()

def basePath(path:str)->str:
    if path.find('/')==-1 and path.find('\\')==-1:
        return cwd()+'/'
    idx=path.rfind('/')
    candidate=path.rfind('\\')
    if candidate>idx:
        idx=candidate
    return path[:idx+1]

def preprocess(path:str,prefix:str='',imported:list[str]=[])->str: # this is not pure func, may cause unexpected effects
    #imported used for avoiding repeated import 
    infile=open(path,'r')
    # outPath=path+'Min.txt'
    # outfile=open(outPath,'w')
    # print(f'prefix is {prefix}')
    imported.append(prefix)
    
    content=infile.read()
    infile.close()
    imports:list[str]=[]
    while 1:
        if content.find('from .')==-1:
            # outfile.write(content)
            break
        else:
            start=content.find('from .')
            div=content.find('\n',start)+1
            imports.append(content[start:div-1])
            content=content[div:]
    L=len(imports)
    if L==0:
        print('imported:',imported)
        return content+'\n'
    res=''
    for i in range(L):
        div1=imports[i].find('.')+1
        div2=imports[i].find(' import ')
        pkg=imports[i][div1:div2].replace('.','/').replace(' ','')
        mod=imports[i][div2+8:].replace(' ','')
        # subPrefix=prefix+'_'+pkg.replace('/','_')
        subPrefix=prefix[:prefix.rfind('_')]+'_'+pkg.replace('/','_')+'_'+mod
        # print(subPrefix)
        subPath=basePath(path)+pkg+'/'+mod+'.py'
        if subPrefix not in imported:
            subContent=preprocess(subPath,subPrefix,imported)
            res+=subContent
        
    print('imported:',imported)
    #用 idx1=content.find('def ') ; idx2=content.find('def ',idx1+4) ... 来 区分函数
    return res+content+'\n'