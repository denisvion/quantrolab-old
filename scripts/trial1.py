import time
print 'Starting...'
t0=time.time()
for i in range(1000):
	print 'ellapse time =%f' % (time.time()-t0)
	time.sleep(0.1)