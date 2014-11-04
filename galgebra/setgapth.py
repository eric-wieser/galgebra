#!/usr/bin/python
#setgapth.py

import os, sys, site

cur_dir = os.path.abspath('.')

if os.name == 'posix' or os.name == 'mac':
    dist_pkgs = site.getsitepackages()[-1]
    pth_name = dist_pkgs + '/Ga.pth'
    os.system('rm -f ' + pth_name)

if os.name == 'nt':
    dist_pkgs = site.getsitepackages()[-1]
    dist_lst = dist_pkgs.split('\\')
    pth_name = dist_lst[0] + '\\' + dist_lst[1] + '\\Ga.pth'
    #pth_name = 'C:\\Python27\\Ga.pth'
    os.system('del ' + pth_name)

pth_file = open(pth_name,'w')
pth_file.write('#Path of Ga module\n'+cur_dir)
pth_file.close()

print 'os name:',os.name
print 'site-packages directory:',pth_name
print 'Ga.pth:'
print os.system('more ' + pth_name)


