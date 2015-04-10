import traj_tools as trj
import matplotlib.pyplot as plt
import numpy as np

c1 = trj.loadme('c1new.trj')
c2 = trj.loadme('c2.trj')

plist = ['300', '400']
hlist = [0.5, 1, 2, 3, 4, 5, 10]
hlist = list(np.arange(0, 6, 1/6.))

totc1 = c1.count_trjs('WCB_Cy1')
totc2 = c2.count_trjs('WCB_Cy1_new')

alist = []
blist = []
clist = []
dlist = []
elist = []

for p in plist:
    print 'Testing:', p
    pmult = float(p) / 600.
    #hnewlist = list(np.array(hlist) * pmult)
    hnewlist = hlist
    for h in hnewlist:
        print 'Maxtime:', h
        if not p == '600':
            c1.create_filter('Test'+ p + str(h), [('P600', 0, 2880), ('P600_stop', 0, 3420),
                                    ('P' + p +'withinP600', 0, h * 60)])
            c2.create_filter('Test'+ p + str(h), [('P600', 0, 2880), ('-10201025', True), 
                                    ('P' + p +'withinP600', 0, h * 60)])
        else:
            c1.create_filter('Test'+ p + str(h), [('P600', 0, 2880), ('P600_stop', 0, 3420),
                                    ('P600', 0, h * 60)])
            c2.create_filter('Test'+ p + str(h), [('P600', 0, 2880), ('-10201025', True), 
                                    ('P600', 0, h * 60)])
        partc1 = c1.count_trjs('Test'+p+ str(h))
        partc2 = c2.count_trjs('Test'+p+ str(h))
        
        mult = 1
        per1 = (partc1 / float(totc1)) * mult
        per2 = (1 - partc2 / float(totc2)) * mult
        alist.append(per1)
        blist.append(per2)
        clist.append((mult - per1)**2 + (mult - per2)**2)
        dlist.append((mult - per1) + (mult - per2))
        elist.append(h)

h4list = hlist * 4

print np.amin(clist), elist[np.argmin(clist)]


plt.plot(alist, marker = '*', color = 'green')
plt.plot(blist, marker = '*', color = 'blue')
plt.plot(clist, marker = '*', color = 'black')
plt.plot(dlist, marker = '*', color = 'red')
plt.grid()
plt.show()