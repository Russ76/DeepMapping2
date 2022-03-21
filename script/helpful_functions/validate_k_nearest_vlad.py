import set_path
import os
import torch
import numpy as np 
from dataset_loader import SimulatedPointCloud
from torch.utils.data import DataLoader

import utils
import scipy.io as sio
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from sklearn.manifold import TSNE
from sklearn.neighbors import NearestNeighbors

from open3d import read_point_cloud

checkpoint_dir = os.path.join('../../','data')
checkpoint_dir_validate = os.path.join('../../results/2D',"gt_map_validate")
if not os.path.exists(checkpoint_dir_validate):
    os.makedirs(checkpoint_dir_validate)

save_name = os.path.join(checkpoint_dir,'database.npy')
best_matrix = np.load(save_name)
best_matrix = torch.tensor(best_matrix, dtype = torch.float64)
best_matrix = np.array(best_matrix)
print("best_matrix:"+str(best_matrix.shape))

data_dir = '/home/cc/dm_data/'
all_folders = sorted(os.listdir(data_dir))

folders = []
# All runs are used for training (both full and partial)
index_list = [5,6,7,9]
print("Number of runs: "+str(len(index_list)))
for index in index_list:
    print("all_folders[index]:"+str(all_folders[index]))
    folders.append(all_folders[index])
print(folders)

all_folders = folders

indices = []
best_matrix_list = []

folder_index = 3
for index,folder in enumerate(all_folders):
    nbrs = NearestNeighbors(n_neighbors=16, algorithm='ball_tree').fit(best_matrix[index])
    distance, indice = nbrs.kneighbors(best_matrix[index])
    best_matrix_embeded = TSNE(n_components=2).fit_transform(best_matrix[index])
    #print("best_matrix[index]:"+str(np.linalg.norm(best_matrix[index][1]-best_matrix[index][2])))
    #ind_nn = tree.query_radius(best_matrix[index],r=0.2)
    #ind_r = tree.query_radius(best_matrix[index],r=50)
    #print("ind_nn:"+str(len(ind_nn)))
    best_matrix_list.append(best_matrix_embeded)
    indices.append(indice)
    #print("indice:"+str(indice))
indices = np.array(indices, dtype=np.int64)
best_matrix_list = np.array(best_matrix_list, dtype=np.float64)

F, N, _ = best_matrix_list.shape
colors = cm.rainbow(np.linspace(0, 1, N))

if not os.path.exists(os.path.join(checkpoint_dir_validate, "pcl_map_TSNE")):
    os.makedirs(os.path.join(checkpoint_dir_validate, "pcl_map_TSNE"))

for f in range(F):
    _, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.scatter(best_matrix_list[f, :, 0], best_matrix_list[f, :, 1], zorder=3, c=colors)
    print("saving figure to "+str(os.path.join(checkpoint_dir_validate, "pcl_map_TSNE", 'unsupervised_tsne_'+str(f)+'.png')))
    plt.savefig(os.path.join(checkpoint_dir_validate, "pcl_map_TSNE", 'unsupervised_tsne'+str(f)+'.png'), bbox_inches='tight')
    plt.close()


init_pose = None

indices_gt = []
indices_gt_true = []

for index,folder in enumerate(all_folders):
    data_dir_f = os.path.join(data_dir, folder) 
    if not os.path.exists(data_dir_f):
        os.makedirs(data_dir_f)
    checkpoint_dir_validate_f = os.path.join(checkpoint_dir_validate, folder)
    if not os.path.exists(checkpoint_dir_validate_f):
        os.makedirs(checkpoint_dir_validate_f)
    gt_file = os.path.join(data_dir_f,'gt_pose.mat')
    gt_pose = sio.loadmat(gt_file)
    gt_pose = gt_pose['pose']
    gt_location = gt_pose[:,:2]
    pose_est = torch.tensor(gt_pose, dtype = torch.float).cpu()
    location_est = torch.tensor(gt_location, dtype = torch.float).cpu()
    #print("pose_est:"+str(pose_est.size()))
    nbrs = NearestNeighbors(n_neighbors=48, algorithm='ball_tree').fit(location_est)
    nbrs_16 = NearestNeighbors(n_neighbors=16, algorithm='ball_tree').fit(location_est)

    distance_, indice_ = nbrs.kneighbors(location_est)
    distance_16, indice_16 = nbrs_16.kneighbors(location_est)

    indice_ = np.array(indice_, dtype=np.int64)
    indice_16 = np.array(indice_16, dtype=np.int64)

    indices_gt.append(indice_)
    indices_gt_true.append(indice_16)

    utils.draw_graphs(location_est, indices[index], 1, checkpoint_dir_validate_f, downsample_size = 32)

indices_gt = np.array(indices_gt, dtype=np.int64)
indices_gt_true = np.array(indices_gt_true, dtype=np.int64)


#### Accuracy ######
B, P, N = indices.shape
total_grid = float(B*P*N)
acc_count = 0.0
aacc_count = 0.0
fp_count = 0.0
afp_count = 0.0
fn_count = 0.0
afn_count = 0.0
false_positive = []
absolute_false_positive = []
false_negative = []
absolute_false_negative = []

for b in range(B):
    for p in range(P):
        for n in range(N):
            if indices[b,p,n] in indices_gt[b,p]:
                acc_count = acc_count + 1
            if indices[b,p,n] in indices_gt_true[b,p]:
                aacc_count = aacc_count + 1
            if (indices[b,p,n] not in indices_gt[b,p]):
                fp_count = fp_count + 1
            if (indices[b,p,n] not in indices_gt_true[b,p]):
                afp_count = afp_count + 1
            if (indices_gt[b,p,n] not in indices[b,p]):
                fn_count = fn_count + 1
            if (indices_gt_true[b,p,n] not in indices[b,p]):
                afn_count = afn_count + 1
                                         
            if (b==0) and (p==0) and (indices[b,p,n] not in indices_gt_true[b,p]):
                false_positive.append(indices[b,p,n])
            if (b==0) and (p==0) and (indices[b,p,n] not in indices_gt[b,p]):
                absolute_false_positive.append(indices[b,p,n])
            if (b==0) and (p==0) and (indices_gt_true[b,p,n] not in indices[b,p]):
                false_negative.append(indices_gt_true[b,p,n])
            if (b==0) and (p==0) and (indices_gt[b,p,n] not in indices[b,p]):            
                absolute_false_negative.append(indices_gt[b,p,n])

print("trained nearest 16 neigbours for packet 0:"+str(indices[0,0]))
print("top 16 nearest neighbours: :"+str(indices_gt_true[0,0]))
print("top nearest 48 neigbours:"+str(indices_gt[0,0]))
print("false_positives for packet 0:"+str(false_positive))
print("false_positives with loose constraint for packet 0:"+str(absolute_false_positive))
print("false_negatives for packet 0:"+str(false_negative))
print("false_negatives with loose constraint for packet 0:"+str(absolute_false_negative))

if not os.path.exists(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_train")):
    os.makedirs(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_train"))

if not os.path.exists(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt")):
    os.makedirs(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt"))

if not os.path.exists(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt_true")):
    os.makedirs(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt_true"))

for index_ in indices_gt_true[0,0]:
    _, ax = plt.subplots()
    ax.set_aspect('equal')
    #print("index_:"+str('{0:04}'.format(index_)))
    pcl = read_point_cloud("/home/cc/dm_data/v0_pose05/00000"+str('{0:04}'.format(index_))+".pcd")
    pcl = np.asarray(pcl.points, dtype=np.float32)
    ax.scatter(pcl[:, 0], pcl[:, 1], zorder=2)
    #print("saving figure to "+str(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt_true", 'unsupervised_'+str(index_)+'.png')))
    plt.savefig(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt_true", 'unsupervised_'+str(index_)+'.png'), bbox_inches='tight')
    plt.close()

for index_ in indices_gt[0,0]:
    _, ax = plt.subplots()
    ax.set_aspect('equal')
    #print("index_:"+str('{0:04}'.format(index_)))
    pcl = read_point_cloud("/home/cc/dm_data/v0_pose05/00000"+str('{0:04}'.format(index_))+".pcd")
    pcl = np.asarray(pcl.points, dtype=np.float32)
    ax.scatter(pcl[:, 0], pcl[:, 1], zorder=2)
    #print("saving figure to "+str(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt", 'unsupervised_'+str(index_)+'.png')))
    plt.savefig(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_gt", 'unsupervised_'+str(index_)+'.png'), bbox_inches='tight')
    plt.close()

for index_ in indices[0,0]:
    _, ax = plt.subplots()
    ax.set_aspect('equal')
    #print("index_:"+str('{0:04}'.format(index_)))
    pcl = read_point_cloud("/home/cc/dm_data/v0_pose05/00000"+str('{0:04}'.format(index_))+".pcd")
    pcl = np.asarray(pcl.points, dtype=np.float32)
    ax.scatter(pcl[:, 0], pcl[:, 1], zorder=2)
    #print("saving figure to "+str(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_train", 'unsupervised_'+str(index_)+'.png')))
    plt.savefig(os.path.join(checkpoint_dir_validate, "pcl_map_Similarity_train", 'unsupervised_'+str(index_)+'.png'), bbox_inches='tight')
    plt.close()

print("################################################")
            #print("indices[b,p,n]:"+str(indices[b,p,n]))
            #print("indices_gt[b,p]:"+str(indices_gt[b,p]))

print("The Precision: "+str(acc_count/(acc_count+fp_count)))
print("The Recall: "+str(acc_count/(acc_count+fn_count)))

save_name = os.path.join(checkpoint_dir,'best_n_trained.npy')

np.save(save_name,indices[0])
print("Done")
