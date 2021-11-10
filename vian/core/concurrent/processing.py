from multiprocessing import Process, Manager


def _run(q, fn, args):
    q.put(fn(*args))


def run_in_subprocess(fn, args):
    queue = Manager().Queue()
    p = Process(target=_run, args=(queue, fn, args))
    p.start()
    p.join()
    return queue.get()


if __name__ == '__main__':
    import numpy as np

    def my_function( x, y):
        return np.zeros(shape=(x * y, 5))

    res = run_in_subprocess(my_function, [100,100])
    print(res)