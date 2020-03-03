import numpy as np
from sklearn.cluster import AgglomerativeClustering

def classification_clustering(X, n_clusters = 1):
    X = tfidf(X)
    clustering = AgglomerativeClustering(n_clusters=n_clusters, compute_full_tree=True).fit(X)
    print(X.shape)
    print(clustering.labels_ )
    print(clustering.children_ )
    print(len(clustering.children_))

def agglomerative_get_iteration(clustering:AgglomerativeClustering, iteration):
    n = len(clustering.children_)


def tfidf(X):
   """
   :param X: a binary matrix (rows are segments, columns are tags)
   :return: a real matrix of the same size as `X`
   """

   tf = X
   idf = np.log(len(X) / np.sum(X, axis=0))
   return tf*idf[None, :]


if __name__ == '__main__':
    from random import randint
    import time
    mat = np.zeros(shape=(1000, 1000))
    for x in range(1000):
        for y in range(1000):
            v = randint(0, 100)
            mat[x, y] = v
            mat[y, x] = v
    t = time.time()

    classification_clustering(mat, i + 1)
    print(time.time() - t)