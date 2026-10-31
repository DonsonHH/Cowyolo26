"""Stable exact TopK using partition, preserving boundary ties by original index."""
import os,numpy as np
def select(x,k,axis=-1,largest=1):
 axis=axis%x.ndim;k=int(k);n=x.shape[axis]
 if n<2048 or not np.isfinite(x).all() or os.environ.get('O6_HEAD_LUT_DISABLE')=='1':
  order=np.argsort(-x if largest else x,axis=axis,kind='stable');idx=np.take(order,np.arange(k),axis=axis).astype(np.int64)
 else:
  rows=np.moveaxis(x,axis,-1);flat=rows.reshape(-1,n);result=np.empty((len(flat),k),np.int64)
  for row,v in enumerate(flat):
   values=-v if largest else v;cut=np.partition(values,k-1)[k-1]
   better=np.flatnonzero(values<cut);ties=np.flatnonzero(values==cut)[:k-len(better)];chosen=np.concatenate((better,ties))
   assert len(chosen)==k
   result[row]=chosen[np.lexsort((chosen,values[chosen]))]
  idx=np.moveaxis(result.reshape(rows.shape[:-1]+(k,)),-1,axis)
 return [np.take_along_axis(x,idx,axis=axis),idx]
