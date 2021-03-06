#!/usr/bin/env python
import numpy as np
import cPickle as pk
import tabular as tb
import itertools
import copy
import sys
import dldata.stimulus_sets.hvm as hvm
from mturkutils.base import MatchToSampleFromDLDataExperiment

REPEATS_PER_QE_IMG = 4
ACTUAL_TRIALS_PER_HIT = 150
LEARNING_PERIOD = 10

def get_exp(sandbox=True, dummy_upload=True):

    dataset = hvm.HvMWithDiscfade()
    meta = dataset.meta
    categories = dataset.categories
    combs = [categories]

    inds = np.arange(len(meta))
    preproc = None
    image_bucket_name = 'hvm_timing'
    urls = dataset.publish_images(inds, preproc,
                                  image_bucket_name,
                                  dummy_upload=dummy_upload)

    base_url = 'https://canonical_images.s3.amazonaws.com/'
    response_images = [{
        'urls': [base_url + cat + '.png' for cat in categories],
        'meta': [{'category': 'Animals'},
                 {'category': 'Boats'},
                 {'category': 'Cars'},
                 {'category': 'Chairs'},
                 {'category': 'Faces'},
                 {'category': 'Fruits'},
                 {'category': 'Planes'},
                 {'category': 'Tables'}],
        'labels': categories}]

    html_data = {
            'response_images': response_images,
            'combs': combs,
            'num_trials': 90 * 64,
            'meta_field': 'category',
            'meta': meta,
            'urls': urls,
            'shuffle_test': True,
    }

    additionalrules = [{'old': 'LEARNINGPERIODNUMBER',
                    'new':  str(LEARNING_PERIOD)}]
    trials_per_hit = ACTUAL_TRIALS_PER_HIT + 32
    exp = MatchToSampleFromDLDataExperiment(
            htmlsrc='hvm_basic_categorization.html',
            htmldst='hvm_basic_categorization_n%05d.html',
            sandbox=sandbox,
            title='Object recognition --- report what you see',
            reward=0.35,
            duration=1500,
            keywords=['neuroscience', 'psychology', 'experiment', 'object recognition'],  # noqa
            description="***You may complete as many HITs in this group as you want*** Complete a visual object recognition task where you report the identity of objects you see. We expect this HIT to take about 10 minutes or less, though you must finish in under 25 minutes.  By completing this HIT, you understand that you are participating in an experiment for the Massachusetts Institute of Technology (MIT) Department of Brain and Cognitive Sciences. You may quit at any time, and you will remain anonymous. Contact the requester with questions or concerns about this experiment.",  # noqa
            comment="hvm basic categorization",  # noqa
            collection_name= 'hvm_basic_categorization',
            max_assignments=1,
            bucket_name='hvm_basic_categorization',
            trials_per_hit=trials_per_hit,  # 150 + 8x4 repeats
            html_data=html_data,
            frame_height_pix=1200,
            othersrc = ['../../lib/dltk.js'],
            additionalrules=additionalrules

            )

    # -- create trials
    exp.createTrials(sampling='with-replacement', verbose=1)
    n_total_trials = len(exp._trials['imgFiles'])
    assert n_total_trials == 90 * 64, n_total_trials

    # -- in each HIT, the followings will be repeated 4 times to
    # estimate "quality" of data

    ind_repeats = [3440, 3282, 3321, 3802, 5000, 3202, 4041, 4200] * REPEATS_PER_QE_IMG
    rng = np.random.RandomState(0)
    rng.shuffle(ind_repeats)
    trials_qe = {e: [copy.deepcopy(exp._trials[e][r]) for r in ind_repeats]
            for e in exp._trials}
    offsets = np.arange(
                ACTUAL_TRIALS_PER_HIT - 3, -1,
                -ACTUAL_TRIALS_PER_HIT / float(len(ind_repeats))
            ).round().astype('int')

    n_hits_floor = n_total_trials / ACTUAL_TRIALS_PER_HIT
    n_applied_hits = 0
    for i_trial_begin in xrange((n_hits_floor - 1) * ACTUAL_TRIALS_PER_HIT,
            -1, -ACTUAL_TRIALS_PER_HIT):
        for k in trials_qe:
            for i, offset in enumerate(offsets):
                exp._trials[k].insert(i_trial_begin + offset, trials_qe[k][i])
        n_applied_hits += 1

    print '** n_applied_hits =', n_applied_hits
    print '** len for each in _trials =', \
            {e: len(exp._trials[e]) for e in exp._trials}

    # -- sanity check
    assert 38 == n_applied_hits, n_applied_hits
    assert len(exp._trials['imgFiles']) == 6976, len(exp._trials['imgFiles'])
    s_ref_labels = set([tuple(e) for e in trials_qe['labels']])
    print(s_ref_labels)
    offsets2 = np.arange(8 * 4)[::-1] + offsets

    ibie = zip(range(0, 6976, trials_per_hit), range(trials_per_hit, 6976 + trials_per_hit, trials_per_hit))
    assert all([set([tuple(e) for e in
        np.array(exp._trials['labels'][ib:ie])[offsets2]]) == s_ref_labels
        for ib, ie in ibie[:-1]])
    print '** Finished creating trials.'

    return exp, html_data


if __name__ == '__main__':
    exp, _ = get_exp(sandbox=False, dummy_upload=True)
    exp.createTrials()
    exp.prepHTMLs()
    exp.testHTMLs()
    exp.uploadHTMLs()
    exp.createHIT(secure=True)

    #hitids = cPickle.load(open('3ARIN4O78FSZNXPJJAE45TI21DLIF1_2014-06-13_16:25:48.143902.pkl'))
    #exp.disableHIT(hitids=hitids)
