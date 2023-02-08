from .d.transpiler import transpile

def f(srcPath:str,outPath:str):
    source = open(srcPath).read()
    cCode = transpile(source)
    if len(outPath)==0:
        outPath = srcPath[:srcPath.rfind('.py')]+'.c'
    outFile = open(outPath,'w')
    outFile.write(cCode)
    outFile.close()
