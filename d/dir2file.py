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

def preprocess(path:str,prefix:str,imported:list[str])->str:
    #imported used for avoiding repeated import, it is actually a global variable for seperate preprocess(...) calls 
    infile=open(path,'r')
    # imported.append(prefix)  换到结尾处理
    
    content=infile.read()
    infile.close()
    imports:list[str]=[]
    while 1:
        if content.find('from .')==-1:
            break
        else:
            start=content.find('from .')
            div=content.find('\n',start)+1
            imports.append(content[start:div-1])
            content=content[div:]
    L=len(imports)
    if prefix!='':
        content=content[content.find('def '):]
        idx1=0
        renameList:list[tuple[str,str]]=[]
        while 1:
            idxL=content.find('(',idx1+4)
            funcName=content[idx1+4:idxL].replace(' ','')
            newFuncName=prefix+'_'+funcName
            # content=content.replace(funcName+'(',newFuncName+'(')  # all functions declared by 'def' is viewed as const func
            renameList.append((' '+funcName+'(',' '+newFuncName+'('))  #调用同文件函数需要在函数名前加空格
            idx1=content.find('\ndef ',idx1+4)
            if idx1==-1:
                break
        for e in renameList:
            content=content.replace(e[0],e[1])
    res=''
    for i in range(L):
        div1=imports[i].find('.')+1
        div2=imports[i].find(' import ')
        pkg=imports[i][div1:div2].replace('.','/').replace(' ','')
        mod=imports[i][div2+8:].replace(' ','')
        subPrefix=prefix[:prefix.rfind('_')]+'_'+pkg.replace('/','_')+'_'+mod
        content=content.replace(mod+'.',subPrefix+'_')
        subPath=basePath(path)+pkg+'/'+mod+'.py'
        if subPrefix not in imported:
            subContent=preprocess(subPath,subPrefix,imported)
            res+=subContent
        
    imported.append(prefix)
    return res+content+'\n'

def wrapper(path:str)->str:
    return preprocess(path,'',[])
def f(path:str,outPath:str)->None:
    if len(outPath)==0:
        outPath=path[:path.rfind('.py')]+'Min.py'
    outFile=open(outPath,'w')
    outFile.write(wrapper(path))
    outFile.close()
