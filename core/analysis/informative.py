import numpy as np
# np.random.seed(1)
from scipy.linalg import get_lapack_funcs, get_blas_funcs


def py_rect_maxvol(A, tol=1., maxK=None, min_add_K=None, minK=None,
        start_maxvol_iters=10, identity_submatrix=True, top_k_index=-1):
    """
    Python implementation of rectangular 2-volume maximization.

    See Also
    --------
    rect_maxvol
    """
    # tol2 - square of parameter tol
    tol2 = tol**2
    # N - number of rows, r - number of columns of matrix A
    N, r = A.shape
    # some work on parameters
    if N <= r:
        return np.arange(N, dtype=np.int32), np.eye(N, dtype=A.dtype)
    if maxK is None or maxK > N:
        maxK = N
    if maxK < r:
        maxK = r
    if minK is None or minK < r:
        minK = r
    if minK > N:
        minK = N
    if min_add_K is not None:
        minK = max(minK, r + min_add_K) 
    if minK > maxK:
        minK = maxK
        #raise ValueError('minK value cannot be greater than maxK value')
    if top_k_index == -1 or top_k_index > N:
        top_k_index = N
    if top_k_index < r:
        top_k_index = r
    # choose initial submatrix and coefficients according to maxvol
    # algorithm
    index = np.zeros(N, dtype=np.int32)
    chosen = np.ones(top_k_index)
    tmp_index, C = py_maxvol(A, 1.05, start_maxvol_iters, top_k_index)
    index[:r] = tmp_index
    chosen[tmp_index] = 0
    C = np.asfortranarray(C)
    # compute square 2-norms of each row in coefficients matrix C
    row_norm_sqr = np.array([chosen[i]*np.linalg.norm(C[i], 2)**2 for
        i in range(top_k_index)])
    # find maximum value in row_norm_sqr
    i = np.argmax(row_norm_sqr)
    K = r
    # set cgeru or zgeru for complex numbers and dger or sger
    # for float numbers
    try:
        ger = get_blas_funcs('geru', [C])
    except:
        ger = get_blas_funcs('ger', [C])
    # augment maxvol submatrix with each iteration
    while (row_norm_sqr[i] > tol2 and K < maxK) or K < minK:
        # add i to index and recompute C and square norms of each row
        # by SVM-formula
        index[K] = i
        chosen[i] = 0
        c = C[i].copy()
        v = C.dot(c.conj())
        l = 1.0/(1+v[i])
        ger(-l,v,c,a=C,overwrite_a=1)
        C = np.hstack([C, l*v.reshape(-1,1)])
        row_norm_sqr -= (l*v[:top_k_index]*v[:top_k_index].conj()).real
        row_norm_sqr *= chosen
        # find maximum value in row_norm_sqr
        i = row_norm_sqr.argmax()
        K += 1
    # parameter identity_submatrix is True, set submatrix,
    # corresponding to maxvol rows, equal to identity matrix
    if identity_submatrix:
        C[index[:K]] = np.eye(K, dtype=C.dtype)
    return index[:K].copy(), C


def py_maxvol(A, tol = 1.05, max_iters = 100, top_k_index = -1):
    """Python implementation of 1-volume maximization. For information see :py:func:`maxvol` function"""
    if tol < 1:
        tol = 1.0
    N, r = A.shape
    if N <= r:
        return np.arange(N, dtype = np.int32), np.eye(N, dtype = A.dtype)
    if top_k_index == -1 or top_k_index > N:
        top_k_index = N
    if top_k_index < r:
        top_k_index = r
    # DGETRF
    B = np.copy(A[:top_k_index], order = 'F')
    C = np.copy(A.T, order = 'F')
    H, ipiv, info = get_lapack_funcs('getrf', [B])(B, overwrite_a = 1)
    # computing pivots from ipiv
    index = np.arange(N, dtype = np.int32)
    for i in range(r):
        tmp = index[i]
        index[i] = index[ipiv[i]]
        index[ipiv[i]] = tmp
    # solve A = CH, H is in LU format
    B = H[:r]
    # It will be much faster to use dtrsm instead of dtrtrs
    trtrs = get_lapack_funcs('trtrs', [B])
    trtrs(B, C, trans = 1, lower = 0, unitdiag = 0, overwrite_b = 1)
    trtrs(B, C, trans = 1, lower = 1, unitdiag = 1, overwrite_b = 1)
    # C has shape (r, N) -- it is stored transposed
    # find max value in C
    i, j = divmod(abs(C[:,:top_k_index]).argmax(), top_k_index)
    # set cgeru or zgeru for complex numbers and dger or sger for float numbers
    try:
        ger = get_blas_funcs('geru', [C])
    except:
        ger = get_blas_funcs('ger', [C])
    # set iters to 0
    iters = 0
    # check if need to swap rows
    while abs(C[i,j]) > tol and iters < max_iters:
        # add j to index and recompute C by SVM-formula
        index[i] = j
        tmp_row = C[i].copy()
        tmp_column = C[:,j].copy()
        tmp_column[i] -= 1.
        alpha = -1./C[i,j]
        ger(alpha, tmp_column, tmp_row, a = C, overwrite_a = 1)
        iters += 1
        i, j = divmod(abs(C[:,:top_k_index]).argmax(), top_k_index)
    return index[:r].copy(), C.T


def select_rows(X, nrows, maxiter=100):
    """
    Given a list of instances, selects a subset of them that are as informative as possible
    
    :param X: a data matrix (rows are instances, columns are attributes)
    :param nrows: how many instances to select
    :param maxiter:
    :return: a list of `nrows` integers
    
    """
    
    assert 1 <= nrows <= X.shape[0]

    idx_i = np.random.choice(np.arange(X.shape[0]), nrows)
    idx_j = np.random.choice(np.arange(X.shape[1]), nrows)
    old_idx_i = idx_i
    old_idx_j = idx_j

    for it in range(maxiter):
        if it % 2 == 0:
            idx_i = py_rect_maxvol(X[:, idx_j], minK=nrows, maxK=nrows)[0]
            assert len(idx_i) == nrows
        else:
            idx_j = py_rect_maxvol(X[idx_i, :].T, minK=nrows, maxK=nrows)[0]
            assert len(idx_j) == nrows
        if np.array_equal(old_idx_i, idx_i) and np.array_equal(old_idx_j, idx_j):
            break
        old_idx_i = idx_i
        old_idx_j = idx_j
    return idx_i

