import numpy as np

class PolyModel():
    def __init__(self, lam=1.0, mu=0.5):
        self.lam = lam
        self.mu = mu
    def init_mesh(self, n=2):
        from ..mesh import TetrahedronMesh
        point = np.array([
            [0, 0, 0],
            [1, 0, 0], 
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1], 
            [1, 1, 1],
            [0, 1, 1]], dtype=np.float) 

        cell = np.array([
            [0,1,2,6],
            [0,5,1,6],
            [0,4,5,6],
            [0,7,4,6],
            [0,3,7,6],
            [0,2,3,6]], dtype=np.int)
        mesh = TetrahedronMesh(point, cell)
        mesh.uniform_refine(n)
        return mesh

    def displacement(self, p):
        x = p[..., 0]
        y = p[..., 1]
        z = p[..., 2]
        val = x*(1-x)*y*(1-y)*z*(1-z) 
        val = np.einsum('...j, k->...jk', val, np.array([2**4, 2**5, 2**6]))
        return val

    def grad_displacement(self, p):
        x = p[..., 0]
        y = p[..., 1]
        z = p[..., 2]
        a, b, c = 2**4, 2**5, 2**6

        shape = p.shape + (3, )
        val = np.zeros(shape, dtype=np.float)
        t0 = (-x + 1)*(-y + 1)*(-z + 1)
        t1 = x*y*z
        val[..., 0, 0] = -a*t1*(-y + 1)*(-z + 1) + a*y*z*t0
        val[..., 0, 1] = -a*t1*(-x + 1)*(-z + 1) + a*x*z*t0
        val[..., 0, 2] = -a*t1*(-x + 1)*(-y + 1) + a*x*y*t0
        val[..., 1, 0] = -b*t1*(-y + 1)*(-z + 1) + b*y*z*t0
        val[..., 1, 1] = -b*t1*(-x + 1)*(-z + 1) + b*x*z*t0
        val[..., 1, 2] = -b*t1*(-x + 1)*(-y + 1) + b*x*y*t0
        val[..., 2, 0] = -c*t1*(-y + 1)*(-z + 1) + c*y*z*t0
        val[..., 2, 1] = -c*t1*(-x + 1)*(-z + 1) + c*x*z*t0
        val[..., 2, 2] = -c*t1*(-x + 1)*(-y + 1) + c*x*y*t0
        return val

    def stress(self, p):
        lam = self.lam
        mu = self.mu
        du = self.grad_displacement(p)
        val = mu*(du + du.swapaxes(-1, -2))
        idx = np.arange(3)
        val[..., idx, idx] += lam*du.trace(axis1=-2, axis2=-1)[..., np.newaxis]
        return val
        

    def compliance_tensor(self, phi):
        lam = self.lam
        mu = self.mu
        aphi = phi.copy()
        idx = np.arange(3)
        aphi[..., idx, idx] -= (lam/(2*mu+3*lam)*aphi.trace(axis1=-2, axis2=-1))[..., np.newaxis]
        aphi /= 2*mu
        return aphi

    def div_stress(self, p):
        return -self.source(p)

    def source(self, p):
        lam = self.lam
        mu = self.mu
        x = p[..., 0]
        y = p[..., 1]
        z = p[..., 2]
        a, b, c = 2**4, 2**5, 2**6
        val = np.zeros(p.shape, dtype=np.float)
        t0 = (-x+1)*(-y+1)*(-z+1) 
        t1 = (-y+1)*(-z+1)
        t2 = (-x+1)*(-z+1)
        t3 = (-x+1)*(-y+1)
        val[..., 0] += 4*a*mu*t1*y*z 
        val[..., 0] -= lam*(-2*a*t1*y*z + b*t0*z - b*t1*x*z - b*t2*y*z + b*x*y*z*(-z + 1) + c*t0*y - c*t1*x*y - c*t3*y*z + c*x*y*z*(-y + 1)) 
        val[..., 0] -= mu*(-2*a*t2*x*z + b*t0*z - b*t1*x*z - b*t2*y*z + b*x*y*z*(-z + 1)) 
        val[..., 0] -= mu*(-2*a*t3*x*y + c*t0*y - c*t1*x*y - c*t3*y*z + c*x*y*z*(-y + 1))

        val[..., 1] += 4*b*mu*t2*x*z 
        val[..., 1] -= lam*(a*t0*z - a*t1*x*z - a*t2*y*z + a*x*y*z*(-z + 1) - 2*b*t2*x*z + c*t0*x - c*t2*x*y - c*t3*x*z + c*x*y*z*(-x + 1)) 
        val[..., 1] -= mu*(a*t0*z - a*t1*x*z - a*t2*y*z + a*x*y*z*(-z + 1) - 2*b*t1*y*z) 
        val[..., 1] -= mu*(-2*b*t3*x*y + c*t0*x - c*t2*x*y - c*t3*x*z + c*x*y*z*(-x + 1))

        val[..., 2] += 4*c*mu*t3*x*y 
        val[..., 2] -= lam*(a*t0*y - a*t1*x*y - a*t3*y*z + a*x*y*z*(-y + 1) + b*t0*x - b*t2*x*y - b*t3*x*z + b*x*y*z*(-x + 1) - 2*c*t3*x*y)
        val[..., 2] -= mu*(a*t0*y - a*t1*x*y - a*t3*y*z + a*x*y*z*(-y + 1) - 2*c*t1*y*z) 
        val[..., 2] -= mu*(b*t0*x - b*t2*x*y - b*t3*x*z + b*x*y*z*(-x + 1) - 2*c*t2*x*z)
        return val