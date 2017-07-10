import numpy as np
from scipy.sparse import coo_matrix, csc_matrix, csr_matrix, spdiags, eye, tril, triu
from .mesh_tools import unique_row
from .Mesh3d import Mesh3d, Mesh3dDataStructure

class TetrahedronMesh(Mesh3d):
    def __init__(self, point, cell, dtype=np.float):
        self.point = point
        N = point.shape[0]
        self.ds = TetrahedronMeshDataStructure(N, cell)

        self.meshtype = 'tet'
        self.dtype= dtype 

    def volume(self):
        cell = self.ds.cell
        point = self.point
        v01 = point[cell[:,1], :] - point[cell[:,0],:]
        v02 = point[cell[:,2], :] - point[cell[:,0],:]
        v03 = point[cell[:,3], :] - point[cell[:,0],:]
        volume = np.sum(v03*np.cross(v01, v02), axis=1)/6.0
        return volume

    def face_area(self):
        face = self.ds.face
        point = self.point
        v01 = point[face[:, 1], :] - point[face[:, 0], :]
        v02 = point[face[:, 2], :] - point[face[:, 0], :]
        dim = self.geom_dimension() 
        nv = np.cross(v01, v02)
        area = np.sqrt(np.square(nv).sum(axis=1))/2.0
        return area 

    def dihedral_angle(self):
        NC = self.number_of_cells()
        point = self.point
        cell = self.ds.cell
        localFace = self.ds.localFace 
        n = [np.cross(point[cell[:, j],:] - point[cell[:, i],:],
            point[cell[:, k],:] - point[cell[:, i],:]) for i, j, k in localFace]
        l =[ np.sqrt(np.sum(ni**2, axis=1)) for ni in n]
        n = [ ni/li.reshape(-1, 1) for ni, li in zip(n, l)]
        localEdge = self.ds.localEdge
        angle = [(np.pi - np.arccos((n[i]*n[j]).sum(axis=1)))/np.pi*180 for i,j in localEdge[-1::-1]]
        return np.array(angle).T


    def bc_to_point(self, bc):
        point = self.point
        cell = self.ds.cell
        return np.tensordot(bc, point[cell,:], axes=(0,1))

    def circumcenter(self):
        point = self.point
        cell = self.ds.cell
        v = [ point[cell[:,0],:] - point[cell[:,i],:] for i in range(1,4)]
        l = [ np.sum(vi**2, axis=1, keepdims=True) for vi in v]
        d = l[2]*np.cross(v[0], v[1]) + l[0]*np.cross(v[1], v[2]) + l[1]*np.cross(v[2],v[0])
        volume = self.volume()
        d /=12*volume.reshape(-1,1)
        c = point[cell[:,0],:] + d
        R = np.sqrt(np.sum(d**2,axis=1))
        return c, R

    def grad_lambda(self):
        localFace = self.ds.localFace
        point = self.point
        cell = self.cell
        NC = self.number_of_cells()
        Dlambda = np.zeros((NC, 4, 3), dtype=self.dtype)
        volume = self.volume()
        for i in range(4):
            j,k,m = localFace[i]
            vjk = point[cell[:,k],:] - point[cell[:,j],:]
            vjm = point[cell[:,m],:] - point[cell[:,j],:]
            Dlambda[:,i,:] = np.cross(vjm, vjk)/(6*volume.reshape(-1,1))
        return Dlambda, volume

    def uniform_refine(self, n=1):
        for i in range(n):
            N = self.number_of_points()
            NC = self.number_of_cells()
            NE = self.number_of_edges()

            point = self.point
            edge = self.ds.edge
            cell = self.ds.cell
            cell2edge = self.ds.cell_to_edge()

            edge2newPoint = np.arange(N, N+NE)
            newPoint = (point[edge[:,0],:]+point[edge[:,1],:])/2.0

            self.point = np.concatenate((point, newPoint), axis=0)

            p = edge2newPoint[cell2edge]
            newCell = np.zeros((8*NC, 4), dtype=np.int)

            newCell[0:4*NC, 3] = cell.flatten('F')
            newCell[0:NC, 0:3] = p[:, [0, 2, 1]]
            newCell[NC:2*NC, 0:3] = p[:, [0, 3, 4]]
            newCell[2*NC:3*NC, 0:3] = p[:, [1, 5, 3]]
            newCell[3*NC:4*NC, 0:3] = p[:, [2, 4, 5]]

            l = np.zeros((NC, 3), dtype=np.float)
            point = self.point
            l[:, 0] = np.sum((point[p[:, 0]] - point[p[:, 5]])**2, axis=1)
            l[:, 1] = np.sum((point[p[:, 1]] - point[p[:, 4]])**2, axis=1)
            l[:, 2] = np.sum((point[p[:, 2]] - point[p[:, 3]])**2, axis=1)

            # Here one should connect the shortest edge
            # idx = np.argmax(l, axis=1)
            idx = np.argmin(l, axis=1)
            T = np.array([
                (1, 3, 4, 2, 5, 0),
                (0, 2, 5, 3, 4, 1),
                (0, 4, 5, 1, 3, 2)
                ])[idx]
            newCell[4*NC:5*NC, 0] = p[range(NC), T[:, 0]]
            newCell[4*NC:5*NC, 1] = p[range(NC), T[:, 1]]
            newCell[4*NC:5*NC, 2] = p[range(NC), T[:, 4]] 
            newCell[4*NC:5*NC, 3] = p[range(NC), T[:, 5]]

            newCell[5*NC:6*NC, 0] = p[range(NC), T[:, 1]]
            newCell[5*NC:6*NC, 1] = p[range(NC), T[:, 2]]
            newCell[5*NC:6*NC, 2] = p[range(NC), T[:, 4]] 
            newCell[5*NC:6*NC, 3] = p[range(NC), T[:, 5]]

            newCell[6*NC:7*NC, 0] = p[range(NC), T[:, 2]]
            newCell[6*NC:7*NC, 1] = p[range(NC), T[:, 3]]
            newCell[6*NC:7*NC, 2] = p[range(NC), T[:, 4]] 
            newCell[6*NC:7*NC, 3] = p[range(NC), T[:, 5]]

            newCell[7*NC:, 0] = p[range(NC), T[:, 3]]
            newCell[7*NC:, 1] = p[range(NC), T[:, 0]]
            newCell[7*NC:, 2] = p[range(NC), T[:, 4]] 
            newCell[7*NC:, 3] = p[range(NC), T[:, 5]]

            N = self.number_of_points()
            self.ds.reinit(N, newCell)

    def print(self):
        print("Point:\n", self.point)
        print("Cell:\n", self.ds.cell)
        print("Edge:\n", self.ds.edge)
        print("Face:\n", self.ds.face)
        print("Face2cell:\n", self.ds.face2cell)
        print("Cell2face:\n", self.ds.cell_to_face())


class TetrahedronMeshDataStructure(Mesh3dDataStructure):
    localFace = np.array([(1, 2, 3),  (0, 3, 2), (0, 1, 3), (0, 2, 1)])
    localEdge = np.array([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
    localFace2edge = np.array([(5, 4, 3), (5, 1, 2), (4, 2, 0), (3, 0, 1)])
    V = 4
    E = 6
    F = 4

    def __init__(self, N, cell):
        super(TetrahedronMeshDataStructure, self).__init__(N, cell)

    def face_to_edge_sign(self):
        face2edge = self.face_to_edge()
        edge = self.edge
        face2edgeSign = np.zeros((NF, FE), dtype=np.bool)
        n = [1, 2, 0]
        for i in range(3):
            face2edgeSign[:, i] = (face[:, n[i]] == edge[face2edge[:, i], 0])
        return face2edgeSign

