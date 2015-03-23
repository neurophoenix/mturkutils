#!/usr/bin/env python
import numpy as np
import cPickle as pk
import tabular as tb
import itertools
import copy
import sys
from mturkutils.base import MatchToSampleFromDLDataExperiment

# 30 closets objects to the "car" basic-level object
SELECTED_BASIC_OBJS = set(
    ['MB29874', 'MB30758', 'MB27585', 'MB31405',
     'antique_furniture_item_18', 'MB29346', 'household_aid_29', 'MB27346',
     'interior_details_033_2', 'lo_poly_animal_TRTL_B', 'MB30798', '04_piano',
     'laptop01', 'jewelry_29', '31_african_drums', 'calc01',
     'lo_poly_animal_DUCK', 'build51', 'foreign_cat', 'MB31188', 'MB30071',
     'womens_Skirt_02M', 'lo_poly_animal_CHICKDEE', '22_acoustic_guitar',
     'kitchen_equipment_knife2', 'interior_details_130_2', 'Colored_shirt_03M',
     'MB30850', 'fast_food_23_1', 'lo_poly_animal_TRANTULA'])
assert len(SELECTED_BASIC_OBJS) == 30
REPEATS_PER_QE_IMG = 4
ACTUAL_TRIALS_PER_HIT = 100


def get_meta(varlev='v0', selected_basic_objs=SELECTED_BASIC_OBJS):
    """Mix the objectome 64 basic-level set and the car subordinate
    level set"""
    assert len(np.unique(selected_basic_objs)) == 30
    meta_cars = pk.load(open('meta_objt_cars_subord_%s.pkl' % varlev))
    meta_basic = pk.load(open('meta_objt_full_64objs.pkl'))

    si = [i for i, e in enumerate(meta_basic)
          if e['obj'] in selected_basic_objs]
    assert len(si) == 30 * 1000

    cnames = list(meta_cars.dtype.names)
    assert list(meta_basic.dtype.names) == cnames
    cnames.remove('internal_canonical')
    cnames.remove('texture')        # contains None
    cnames.remove('texture_mode')   # contains None

    meta = tb.tabarray(
        columns=[np.concatenate([meta_basic[e][si], meta_cars[e]])
                 for e in cnames],
        names=cnames)
    assert len(meta) == 30 * 1000 * 2
    assert len(np.unique(meta['obj'])) == 60   # 30 non-cars + 30 cars
    return meta, meta_basic, meta_cars


def get_urlbase(obj, varlev, selected_basic_objs=SELECTED_BASIC_OBJS):
    if obj in selected_basic_objs:
        return 'https://s3.amazonaws.com/objectome32_final/'
    else:
        return 'https://s3.amazonaws.com/dicarlocox-rendered-imagesets/' \
            'objectome_cars_subord_%s/' % varlev


def get_url(obj, idstr, varlev, resized=True):
    if resized:
        return get_urlbase(obj, varlev) + '360x360/' + idstr + '.png'
    return get_urlbase(obj, varlev) + idstr + '.png'


def get_url_labeled_resp_img(obj, varlev):
    s = get_urlbase(obj, varlev) + 'label_imgs/' + obj + '_label.png'
    s = s.replace('_v0/', '/')
    s = s.replace('_v3/', '/')
    return s


def get_exp_core(varlev, sandbox=True, partial=False,
                 selected_basic_objs=SELECTED_BASIC_OBJS):
    meta, _, meta_cars = get_meta(varlev=varlev)
    cars = np.unique(meta_cars['obj'])
    combs = [(o1, o2) for o1 in selected_basic_objs for o2 in cars] + \
            [e for e in itertools.combinations(cars, 2)]
    urls = [get_url(e['obj'], e['id'], varlev) for e in meta]
    response_images = [{
        'urls': [get_url_labeled_resp_img(o1, varlev),
                 get_url_labeled_resp_img(o2, varlev)],
        'meta': [{'obj': o} for o in [o1, o2]],
        'labels': [o1, o2]
        } for o1, o2 in combs]

    html_data = {
        'response_images': response_images,
        'combs': combs,
        'num_trials': 125 * 2,
        'meta_field': 'obj',
        'meta': meta,
        'urls': urls,
        'shuffle_test': True,
    }

    exp = MatchToSampleFromDLDataExperiment(
            htmlsrc='web/cars_subord.html',
            htmldst='cars_subord_n%05d.html',
            sandbox=sandbox,
            title='Object recognition --- report what you see',
            reward=0.15,
            duration=1600,
            keywords=['neuroscience', 'psychology', 'experiment', 'object recognition'],  # noqa
            description="***You may complete as many HITs in this group as you want*** Complete a visual object recognition task where you report the identity of objects you see. We expect this HIT to take about 5 minutes or less, though you must finish in under 25 minutes.  By completing this HIT, you understand that you are participating in an experiment for the Massachusetts Institute of Technology (MIT) Department of Brain and Cognitive Sciences. You may quit at any time, and you will remain anonymous. Contact the requester with questions or concerns about this experiment.",  # noqa
            comment="objectome_cars_subord.  30 cars and 30 non-cars",  # noqa
            collection_name='objectome_cars_subord_v0v3',
            max_assignments=1,
            bucket_name='objectome_cars_subord_v0v3',
            trials_per_hit=ACTUAL_TRIALS_PER_HIT + 16,  # 100 + 4x4 repeats
            tmpdir='tmp',
            html_data=html_data,
            frame_height_pix=1200,
            othersrc=['../../lib/dltk.js', '../../lib/dltkexpr.js', '../../lib/dltkrsvp.js'],   # noqa
            set_destination=True,
            )

    if partial:
        return exp
    # -- create trials
    exp.createTrials(sampling='with-replacement', verbose=1)
    return exp


def get_exp(sandbox=True, debug=False):
    print '** Creating V0...'
    exp_v0 = get_exp_core('v0', sandbox=sandbox)
    print '** Creating V3...'
    exp_v3 = get_exp_core('v3', sandbox=sandbox)

    if debug:
        return exp_v0, exp_v3

    # -- low-level manipulation of exp to interleave v0 and v3
    # exp = copy.deepcopy(exp_v0)    # doesn't work
    print
    print '** Interleaving V0 and V3...'
    exp = get_exp_core('v3', sandbox=sandbox, partial=True)
    exp._trials = {}
    ks = exp_v0._trials.keys()

    for k in ks:
        n_rej = 0
        # reverse things in v0 to avoid overlapping similar trials
        exp_v0._trials[k].reverse()
        # reset exp
        exp._trials[k] = []
        n = len(exp_v0._trials[k])
        assert n == len(exp_v3._trials[k])
        for i in xrange(n):
            e0 = exp_v0._trials[k][i]
            exp._trials[k].append(e0)
            if exp_v3._trials['imgData'][i]['Sample']['obj'] in \
                    SELECTED_BASIC_OBJS:
                # skip v3 trials when an obj is presented (b/c already in v0)
                n_rej += 1
                continue
            e3 = exp_v3._trials[k][i]
            exp._trials[k].append(e3)
        assert n_rej == 30 * 30 * 125

    n_total_trials = len(exp._trials['imgFiles'])
    assert n_total_trials == (30 * 29 / 2 + 30 * 30) * 250 * 2 - n_rej
    assert (len([0 for e in exp._trials['imgFiles'] if '_v0/' in e[0]]) ==
            len([0 for e in exp._trials['imgFiles'] if '_v3/' in e[0]]) ==
            30*29/2*250 + 30*30*125)
    assert (len([0 for e in exp._trials['imgFiles'] if '_v0/' in e[0] and
                 ('objectome32_final/' in e[1][0] or
                  'objectome32_final/' in e[1][1])]) ==
            len([0 for e in exp._trials['imgFiles'] if '_v3/' in e[0] and
                 ('objectome32_final/' in e[1][0] or
                  'objectome32_final/' in e[1][1])]) ==
            30*30*125)
    assert (len([0 for e in exp._trials['imgFiles'] if
                 'objectome32_final/' in e[0] and
                 ('objectome_cars_subord/' in e[1][0] or
                  'objectome_cars_subord/' in e[1][1])]) ==
            30*30*125)

    # -- in each HIT, the followings will be repeated 4 times to
    # estimate "quality" of data
    ind_repeats = [48, 12, 21, 24] * REPEATS_PER_QE_IMG
    rng = np.random.RandomState(0)
    rng.shuffle(ind_repeats)
    trials_qe = {e: [copy.deepcopy(exp._trials[e][r]) for r in ind_repeats]
                 for e in exp._trials}

    # -- flip answer choices of some repeated images
    n_qe = len(trials_qe['imgFiles'])
    print '** n_qe =', n_qe
    # if True, flip
    flips = [True] * (n_qe / 2) + [False] * (n_qe - n_qe / 2)
    assert len(flips) == n_qe
    rng.shuffle(flips)
    assert len(trials_qe.keys()) == 4

    for i, flip in enumerate(flips):
        if not flip:
            continue
        trials_qe['imgFiles'][i][1].reverse()
        trials_qe['labels'][i].reverse()
        trials_qe['imgData'][i]['Test'].reverse()

    # -- actual application
    offsets = np.arange(
        ACTUAL_TRIALS_PER_HIT - 3, -1,
        -ACTUAL_TRIALS_PER_HIT / float(len(ind_repeats))
    ).round().astype('int')
    assert len(offsets) == len(offsets)

    n_hits_floor = n_total_trials / ACTUAL_TRIALS_PER_HIT
    n_applied_hits = 0
    for i_trial_begin in xrange((n_hits_floor - 1) * ACTUAL_TRIALS_PER_HIT,
                                -1, -ACTUAL_TRIALS_PER_HIT):
        for k in trials_qe:
            for i, offset in enumerate(offsets):
                exp._trials[k].insert(i_trial_begin + offset, trials_qe[k][i])
                # exp._trials[k].insert(i_trial_begin + offset, 'test')
        n_applied_hits += 1

    print '** n_applied_hits =', n_applied_hits
    print '** len for each in _trials =', \
        {e: len(exp._trials[e]) for e in exp._trials}

    # -- sanity check
    assert 5550 == n_applied_hits
    assert len(exp._trials['imgFiles']) == 5550 * (100 + 16)
    s_ref_labels = [tuple(e) for e in trials_qe['labels']]
    print '**', s_ref_labels
    offsets2 = np.arange(16)[::-1] + offsets
    ibie = zip(range(0, 5550 * 116, 116), range(5551 * 116, 116))
    assert all(
        [[(e1, e2) for e1, e2 in
         np.array(exp._trials['labels'][ib:ie])[offsets2]] == s_ref_labels
         for ib, ie in ibie])

    # -- drop unneeded, potentially abusable stuffs
    del exp._trials['imgData']
    del exp._trials['meta_field']
    print '** Finished creating trials.'

    return exp


def main(argv=[], partial=False):
    sandbox = True
    if len(argv) > 1 and argv[1] == 'production':
        sandbox = False
        print '** Creating production HITs'
    else:
        print '** Sandbox mode'
        print '** Enter "driver.py production" to publish production HITs.'

    exp = get_exp(sandbox=sandbox)
    exp.prepHTMLs()
    print '** Done prepping htmls.'
    if partial:
        return exp

    exp.testHTMLs()
    print '** Done testing htmls.'
    exp.uploadHTMLs()
    exp.createHIT(secure=True)
    return exp


if __name__ == '__main__':
    main(sys.argv)