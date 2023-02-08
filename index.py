def f():
    src=input('source path: ')
    dst=input('target dir(default is where source python file is): ')
    # compiler=input('compiler name or path(default is clang): ')
    idx=max(src.rfind('/'),src.rfind('\\'))
    import subprocess
    if len(dst)==0:
        import os
        if idx==-1:
            dst=os.getcwd()
        else:
            dst=src[:idx]
        os.chdir(dst)
        subprocess.call('mkdir target',shell=True)
        dst+='/target/'
    if dst[-1]!='/' and dst[-1]!='\\':
        dst+='/'
    # if len(compiler)==0:
    #     compiler='clang'
    import d.dir2file as d2f
    outFileName=src[idx+1:src.rfind('.py')]
    d2f.f(src,dst+outFileName+'Min.py')
    import d.p2c as p2c
    p2c.f(dst+outFileName+'Min.py',dst+outFileName+'.c')
    
    # subprocess.call([compiler,'-Ofast','-shared','-fPIC',
    #     dst+outFileName+'.c','-o',dst+outFileName+'.so'])
    
if __name__=='__main__':
    f()