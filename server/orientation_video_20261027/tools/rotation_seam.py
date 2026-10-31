"""Restore native coordinates before ByteTrack, never rotate the counting ROI."""
import functools
import numpy as np
from ultralytics.engine.results import Results


def clockwise_boxes(boxes,height):
    values=np.asarray(boxes,dtype=np.float64).reshape(-1,4)
    return np.stack([height-values[:,3],values[:,0],height-values[:,1],values[:,2]],axis=1)


def counterclockwise_boxes(boxes,native_height):
    values=np.asarray(boxes,dtype=np.float64).reshape(-1,4)
    return np.stack([values[:,1],native_height-values[:,2],values[:,3],native_height-values[:,0]],axis=1)


def geometry_controls():
    native=np.array([[0.,0.,2560.,1440.],[100.5,20.25,300.75,680.5],[0.,0.,1.,1.]])
    turned=clockwise_boxes(native,1440)
    assert np.array_equal(counterclockwise_boxes(turned,1440),native)
    toy=np.arange(15,dtype=np.uint8).reshape(3,5)
    assert np.array_equal(np.rot90(np.rot90(toy,k=-1),k=1),toy)
    return {'box_edge_roundtrip_max_error':0.,'pixel_permutation_inverse_verified':True}


def callback_order(model,callback):
    functions=[getattr(c,'func',c) for c in model.predictor.callbacks['on_predict_postprocess_end']]
    rows=[{'name':getattr(c,'__name__',''),'module':getattr(c,'__module__','')} for c in functions]
    index=next(i for i,r in enumerate(rows) if r['name']=='on_predict_postprocess_end' and r['module']=='ultralytics.trackers.track')
    assert functions.index(callback)<index
    assert type(model.predictor.trackers[0]).__name__=='BYTETracker'
    return rows


def make_restore_callback(orientation,holder,fps,raw_rows,hook_frames,seam_checks):
    assert orientation in ['original','clockwise90']
    def restore_before_tracker(predictor):
        assert len(predictor.results)==1
        result=predictor.results[0]
        image=holder['image'];frame=holder['frame_index'];height,width=image.shape[:2]
        expected=(height,width) if orientation=='original' else (width,height)
        assert result.orig_shape==expected and result.orig_img.shape[:2]==expected
        boxes=result.boxes
        assert boxes is not None and boxes.id is None and boxes.data.shape[1]==6
        input_boxes=boxes.xyxy.detach().cpu().numpy().astype(float)
        native_boxes=input_boxes if orientation=='original' else counterclockwise_boxes(input_boxes,height)
        if orientation=='clockwise90':
            values=boxes.data.clone()
            values[:,0]=boxes.data[:,1]
            values[:,1]=height-boxes.data[:,2]
            values[:,2]=boxes.data[:,3]
            values[:,3]=height-boxes.data[:,0]
            mapped=Results(orig_img=image,path=result.path,names=result.names,boxes=values,speed=result.speed)
            native_actual=mapped.boxes.xyxy.detach().cpu().numpy().astype(float)
            max_diff=float(np.max(np.abs(native_actual-native_boxes))) if len(input_boxes) else 0.
            # Record the actual float32 subtraction rounding, not hidden by
            # claiming a double-precision exact mapping of neural outputs.
            assert max_diff<=.00025
            predictor.results[0]=mapped
        else:
            mapped=result;native_actual=input_boxes;max_diff=0.
        assert mapped.orig_shape==(height,width) and mapped.orig_img.shape[:2]==(height,width)
        assert mapped.boxes.id is None
        for original,transformed,conf in zip(input_boxes,native_actual,boxes.conf.detach().cpu().tolist()):
            raw_rows.append({'frame':frame,'time_s':frame/fps,'confidence':conf,
                             'input_x1':original[0],'input_y1':original[1],'input_x2':original[2],'input_y2':original[3],
                             'x1':transformed[0],'y1':transformed[1],'x2':transformed[2],'y2':transformed[3]})
        hook_frames.append(frame)
        seam_checks.append({'frame':frame,'native_H':height,'native_W':width,
                            'input_H':expected[0],'input_W':expected[1],'detector_boxes':len(input_boxes),
                            'max_float32_inverse_difference':max_diff,
                            'native_coordinates_restored_before_tracker':True})
    return restore_before_tracker
