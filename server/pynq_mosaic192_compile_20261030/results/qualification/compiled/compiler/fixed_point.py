import numpy as np
def coefficients(ratios):
    ratios=np.asarray(ratios,dtype=np.float64)
    assert np.all(ratios>0)
    mantissa,exponent=np.frexp(ratios)
    multiplier=np.rint(mantissa*(1<<31)).astype(np.int64);shift=31-exponent
    boundary=multiplier==(1<<31);multiplier[boundary]//=2;shift[boundary]-=1
    # Extra-small ratios can still use the maximal supported shift.
    small=shift>63;multiplier[small]=np.rint(ratios[small]*2.0**63).astype(np.int64);shift[small]=63
    assert np.all((multiplier>=0)&(multiplier<(1<<31))) and np.all((shift>=0)&(shift<=63))
    return multiplier.astype(np.uint32),shift.astype(np.uint32)
def requantize(acc,multiplier,shift,zp):
    shape=(-1,)+(1,)*(acc.ndim-1)
    product=acc.astype(np.int64)*np.asarray(multiplier,dtype=np.int64).reshape(shape)
    mag=np.abs(product).astype(np.uint64);s=np.asarray(shift,dtype=np.uint64).reshape(shape)
    quotient=mag>>s;rem=mag&((np.uint64(1)<<s)-np.uint64(1))
    half=np.uint64(1)<<np.maximum(s,1)-np.uint64(1)
    increment=(s!=0)&((rem>half)|((rem==half)&((quotient&1)!=0)))
    rounded=(quotient+increment).astype(np.int64)
    rounded=np.where(product<0,-rounded,rounded)
    return np.clip(rounded+int(zp),-128,127).astype(np.int8)
def silu_lut(input_scale,input_zp,output_scale,output_zp):
    codes=np.arange(256,dtype=np.uint8).view(np.int8)
    x=(codes.astype(np.float32)-int(input_zp))*np.float32(input_scale)
    sigmoid=np.empty_like(x);positive=x>=0
    sigmoid[positive]=1/(1+np.exp(-x[positive]));e=np.exp(x[~positive]);sigmoid[~positive]=e/(1+e)
    exact=x*sigmoid
    quant=np.clip(np.rint(exact/np.float32(output_scale))+int(output_zp),-128,127).astype(np.int8)
    return quant,exact
