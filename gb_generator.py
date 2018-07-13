
#!/usr/bin/env python

import sys
import numpy as np
from numpy import dot, cross
from numpy.linalg import det, norm
import csl_generator as cslgen

Usage = """

 The code runs in one mode only and takes all necessary options to
 write a final GB structure from the input io_file, which is written
 after you run csl_generator.py. Add the GB_plane of interest from the
 CS planes list (GB1) after running csl_generator.py in second mode.

 "python gb_generator.py io_file"

 """

class GB_character:

    def __init__(self):
        self.axis = np.array([1, 0, 0])
        self.sigma = 1
        self.theta = 0
        self.m = 1
        self.n = 1
        self.R = np.eye(1)
        self.basis = 'fcc'
        self.LatP = 4.05
        self.gbplane = np.array([1, 1, 1])
        self.ortho1 = np.eye(3)
        self.ortho2 = np.eye(3)
        self.ortho = np.eye(3)
        self.atoms = np.eye(3)
        self.atoms1 = np.eye(3)
        self.atoms2 = np.eye(3)
        self.rot1 = np.eye(3)
        self.rot2 = np.eye(3)
        self.Num = 0
        self.dim = np.array([1, 1, 1])
        self.overD = 0
        self.whichG = 'g1'
        self.trans = False

    def ParseGB(self, axis, basis, LatP, m, n, gb):
        self.axis = np.array(axis)
        self.m = int(m)
        self.n = int(n)
        self.sigma = cslgen.get_cubic_sigma(self.axis, self.m, self.n)
        self.theta = cslgen.get_cubic_theta(self.axis, self.m, self.n)
        self.R = cslgen.rot(self.axis, self.theta)

        if (str(basis) == 'fcc' or str(basis) == 'bcc' or str(basis) == 'sc' or
           str(basis) == 'diamond'):

            self.basis = str(basis)

            self.LatP = float(LatP)
            self.gbplane = np.array(gb)

            try:
                self.ortho1, self.ortho2, self.Num = cslgen.Find_Orthogonal_cell(
                            self.basis, self.axis, self.m, self.n, self.gbplane)

            except:
                print("""
                    Could not find the orthogonal cells.... Most likely the
                    input GB_plane is "NOT" a CSL plane. Go back to the first
                    script and double check!
                    """)
                sys.exit()
        else:
            print("Sorry! For now only works for cubic lattices ... ")
            sys.exit()

    def WriteGB(self, *args):

        if len(args) == 8:
            self.overD = float(args[0])
            self.whichG = str(args[1])
            self.trans = args[2]
            a = int(args[3])
            b = int(args[4])
            self.dim = np.array([int(args[5]), int(args[6]), int(args[7])])
            xdel, ydel, x_indice, y_indice = self.Find_overlapping_Atoms()
            print ("<<------ {} atoms are being removed! ------>>"
                   .format(len(xdel)))

            if self.whichG == "G1" or self.whichG == "g1":
                self.atoms1 = np.delete(self.atoms1, x_indice, axis=0)
                xdel[:, 0] = xdel[:, 0] + norm(self.ortho1[:, 0])
                self.atoms1 = np.vstack((self.atoms1, xdel))

            elif self.whichG == "G2" or self.whichG == "g2":
                self.atoms2 = np.delete(self.atoms2, y_indice, axis=0)
                ydel[:, 0] = ydel[:, 0] - norm(self.ortho1[:, 0])
                self.atoms2 = np.vstack((self.atoms2, ydel))

            else:
                print("You must choose either 'g1', 'g2' ")
                sys.exit()

            self.Expand_Super_cell()

            if not self.trans:
                count = 0
                self.Write_to_Lammps(count)
            elif self.trans:
                self.Translate(a, b)

        elif len(args) == 6:

            self.trans = (args[0])
            a = int(args[1])
            b = int(args[2])
            self.dim = np.array([int(args[3]), int(args[4]), int(args[5])])
            self.Expand_Super_cell()

            if not self.trans:
                count = 0
                self.Write_to_Lammps(count)
            elif self.trans:

                self.Translate(a, b)

    def CSL_Ortho_unitcell_atom_generator(self):

        # The fastest way of building unitcells:

        Or = self.ortho.T
        LoopBound = np.zeros((3, 2), dtype=float)
        transformed = []
        CubeCoords = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0],
                              [0, 1, 1], [1, 0, 1], [1, 1, 1], [0, 0, 0]],
                              dtype=float)
        for i in range(len(CubeCoords)):
            transformed.append(np.dot(Or.T, CubeCoords[i]))

        # Finding bounds for atoms in a CSL unitcell:

        LoopBound[0, :] = [min(np.array(transformed)[:, 0]),
                           max(np.array(transformed)[:, 0])]
        LoopBound[1, :] = [min(np.array(transformed)[:, 1]),
                           max(np.array(transformed)[:, 1])]
        LoopBound[2, :] = [min(np.array(transformed)[:, 2]),
                           max(np.array(transformed)[:, 2])]

        # Filling up the unitcell:

        Tol = 1
        x = np.arange(LoopBound[0, 0] - Tol, LoopBound[0, 1] + Tol + 1, 1)
        y = np.arange(LoopBound[1, 0] - Tol, LoopBound[1, 1] + Tol + 1, 1)
        z = np.arange(LoopBound[2, 0] - Tol, LoopBound[2, 1] + Tol + 1, 1)
        V = len(x) * len(y) * len(z)
        indice = (np.stack(np.meshgrid(x, y, z)).T).reshape(V, 3)
        Base = cslgen.Basis(str(self.basis))
        Atoms = []
        tol = 0.001

        # produce Atoms:

        for i in range(V):
            for j in range(len(Base)):
                Atoms.append(indice[i, 0:3] + Base[j, 0:3])
        Atoms = np.array(Atoms)

        # Cell conditions
        Con1 = dot(Atoms, Or[0]) / norm(Or[0]) + tol
        Con2 = dot(Atoms, Or[1]) / norm(Or[1]) + tol
        Con3 = dot(Atoms, Or[2]) / norm(Or[2]) + tol
        # Application of the conditions:
        Atoms = (Atoms[(Con1 >= 0) & (Con1 <= norm(Or[0])) & (Con2 >= 0) &
                 (Con2 <= norm(Or[1])) &
                 (Con3 >= 0) & (Con3 <= norm(Or[2]))])

        if len(Atoms) == (round(det(Or) * len(Base), 7)).astype(int):
            self.Atoms = Atoms
        else:
            self.Atoms = None
        return

    def CSL_Bicrystal_Atom_generator(self):

        Or_1 = self.ortho1.T
        Or_2 = self.ortho2.T

        self.rot1 = np.array([Or_1[0, :] / norm(Or_1[0, :]),
                             Or_1[1, :] / norm(Or_1[1, :]),
                             Or_1[2, :] / norm(Or_1[2, :])])
        self.rot2 = np.array([Or_2[0, :] / norm(Or_2[0, :]),
                             Or_2[1, :] / norm(Or_2[1, :]),
                             Or_2[2, :] / norm(Or_2[2, :])])

        self.ortho = self.ortho1.copy()
        self.CSL_Ortho_unitcell_atom_generator()
        self.atoms1 = self.Atoms

        self.ortho = self.ortho2.copy()
        self.CSL_Ortho_unitcell_atom_generator()
        self.atoms2 = self.Atoms

        self.atoms1 = dot(self.rot1, self.atoms1.T).T
        self.atoms2 = dot(self.rot2, self.atoms2.T).T
        self.atoms2[:, 0] = self.atoms2[:, 0] - norm(Or_2[0, :])
        # print(self.atoms2, norm(Or_2[0, :]) )
        return

    def Expand_Super_cell(self):
        a = norm(self.ortho1[:, 0])
        b = norm(self.ortho1[:, 1])
        c = norm(self.ortho1[:, 2])
        dimX, dimY, dimZ = self.dim

        X = self.atoms1.copy()
        Y = self.atoms2.copy()

        X_new = []
        Y_new = []
        for i in range(dimX):
            for j in range(dimY):
                for k in range(dimZ):
                    Position1 = [i * a, j * b, k * c]
                    Position2 = [-i * a, j * b, k * c]
                    for l in range(len(X)):
                        X_new.append(Position1[0:3] + X[l, 0:3])
                    for m in range(len(Y)):
                        Y_new.append(Position2[0:3] + Y[m, 0:3])

        self.atoms1 = np.array(X_new)
        self.atoms2 = np.array(Y_new)

        return

    def Find_overlapping_Atoms(self):

        IndX = np.where([self.atoms1[:, 0] < 1])[1]
        IndY = np.where([self.atoms2[:, 0] > -1])[1]
        X_new = self.atoms1[self.atoms1[:, 0] < 1]
        Y_new = self.atoms2[self.atoms2[:, 0] > -1]
        x = np.arange(0, len(X_new), 1)
        y = np.arange(0, len(Y_new), 1)
        indice = (np.stack(np.meshgrid(x, y)).T).reshape(len(x) * len(y), 2)
        norms = norm(X_new[indice[:, 0]] - Y_new[indice[:, 1]], axis=1)
        indice_x = indice[norms < self.overD][:, 0]
        indice_y = indice[norms < self.overD][:, 1]
        X_del = X_new[indice_x]
        Y_del = Y_new[indice_y]
        return (X_del, Y_del, IndX[indice_x], IndY[indice_y])

    def Translate(self, a, b):

        tol = 0.001

        if (1 - cslgen.ang(self.gbplane, self.axis) < tol):

            M1, M2 = cslgen.Create_minimal_cell_Method_1(
                     self.sigma, self.axis, self.R)
            D = (1 / self.sigma * cslgen.DSC_vec(self.basis, self.sigma, M1))
            Dvecs = cslgen.DSC_on_plane(D, self.gbplane)
            TransDvecs = np.round(dot(self.rot1, Dvecs), 7)
            shift1 = TransDvecs[:, 0] / 2
            shift2 = TransDvecs[:, 1] / 2
            a = b = 3
        else:
            #a = 10
            #b = 5
            if norm(self.ortho1[:, 1]) > norm(self.ortho1[:, 2]):

                shift1 = (1 / a) * (norm(self.ortho1[:, 1]) *
                                    np.array([0, 1, 0]))
                shift2 = (1 / b) * (norm(self.ortho1[:, 2]) *
                                    np.array([0, 0, 1]))
            else:
                shift1 = (1 / a) * (norm(self.ortho1[:, 2]) *
                                    np.array([0, 0, 1]))
                shift2 = (1 / b) * (norm(self.ortho1[:, 1]) *
                                    np.array([0, 1, 0]))
        print("<<------ {} GB structures are being created! ------>>"
              .format(int(a*b)))

        XX = self.atoms1
        count = 0
        for i in range(a):
            for j in range(b):
                count += 1
                shift = i * shift1 + j * shift2
                atoms1_new = XX.copy() + shift
                self.atoms1 = atoms1_new
                self.Write_to_Lammps(count)

    def Write_to_Lammps(self, trans):

        name = 'input_G'
        plane = str(self.gbplane[0])+str(self.gbplane[1])+str(self.gbplane[2])
        if self.overD > 0:
            overD = str(self.overD)
        else:
            overD = str(None)
        Trans = str(trans)
        # tol = 0.001
        X = self.atoms1.copy()
        Y = self.atoms2.copy()

        NumberAt = len(X) + len(Y)
        X_new = X * self.LatP
        Y_new = Y * self.LatP
        dimx, dimy, dimz = self.dim

        xlo = -1 * np.round(norm(self.ortho1[:, 0]) * dimx * self.LatP, 8)
        xhi = np.round(norm(self.ortho1[:, 0]) * dimx * self.LatP, 8)
        ylo = 0.0
        yhi = np.round(norm(self.ortho1[:, 1]) * dimy * self.LatP, 8)
        zlo = 0.0
        zhi = np.round(norm(self.ortho1[:, 2]) * dimz * self.LatP, 8)

        Type1 = np.ones(len(X_new), int).reshape(1, -1)
        Type2 = 2 * np.ones(len(Y_new), int).reshape(1, -1)
        # Type = np.concatenate((Type1, Type2), axis=1)

        Counter = np.arange(1, NumberAt + 1).reshape(1, -1)

        # data = np.concatenate((X_new, Y_new))
        W1 = np.concatenate((Type1.T, X_new), axis=1)
        W2 = np.concatenate((Type2.T, Y_new), axis=1)
        Wf = np.concatenate((W1, W2))
        FinalMat = np.concatenate((Counter.T, Wf), axis=1)

        with open(name + plane + '_' + overD + '_' +Trans, 'w') as f:
            f.write('#Header \n \n')
            f.write('{} atoms \n \n'.format(NumberAt))
            f.write('2 atom types \n \n')
            f.write('{0:.8f} {1:.8f} xlo xhi \n'.format(xlo, xhi))
            f.write('{0:.8f} {1:.8f} ylo yhi \n'.format(ylo, yhi))
            f.write('{0:.8f} {1:.8f} zlo zhi \n\n'.format(zlo, zhi))
            f.write('Atoms \n \n')
            np.savetxt(f, FinalMat, fmt='%i %i %.8f %.8f %.8f')
        f.close()

    def __str__(self):
        return "GB_character"


def main():

    import yaml

    if len(sys.argv) == 2:
        io_file = sys.argv[1]
        file = open(io_file, 'r')
        in_params = yaml.load(file)

        try:
            axis = np.array(in_params['axis'])
            m = int(in_params['m'])
            n = int(in_params['n'])
            basis = str(in_params['basis'])
            gbplane = np.array(in_params['GB_plane'])
            LatP = in_params['lattice_parameter']
            overlap = in_params['overlap_distance']
            whichG = in_params['which_g']
            rigid = in_params['rigid_trans']
            a = in_params['a']
            b = in_params['b']
            dim1, dim2, dim3 = in_params['dimensions']

        except:
            print('Make sure the input argumnets in io_file are'
                  'put in correctly!')
            sys.exit()

        ###################

        gbI = GB_character()
        gbI.ParseGB(axis, basis, LatP, m, n, gbplane)
        gbI.CSL_Bicrystal_Atom_generator()

        if overlap > 0:
            gbI.WriteGB(overlap, whichG, rigid, a, b, dim1, dim2, dim3)

        elif overlap == 0:
            gbI.WriteGB(rigid, a, b, dim1, dim2, dim3)

    else:
        print(Usage)
    return


if __name__ == '__main__':
    main()