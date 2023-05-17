'''
This script contains the functions used to calculate individual metrics
for different aspects of ribosome profiling data. The functions are called
are called from qc and the input data comes from the output of their
respective modules

'''

import pandas as pd
import math


def read_length_distribution_metric(
        rld_dict: dict,
        ) -> pd.DataFrame:
    """
    Calculate the read length distribution metric from the output of
    the read_length_distribution module.

    This metric is the IQR of the read length distribution and is
    calculated as the difference between the 75th and 25th percentile

    Inputs:
        rld_dict: Dictionary containing the output of the
                read_length_distribution module

    Outputs:
        rld_df: Dataframe containing the read length distribution metric
    """
    rld_df = pd.DataFrame.from_dict(rld_dict, orient="index")
    rld_df = rld_df.reset_index()
    rld_df.columns = ["read_length", "read_count"]

    Q3 = rld_df["read_length"].quantile(0.75)
    Q1 = rld_df["read_length"].quantile(0.25)

    return Q3 - Q1


def ligation_bias_distribution_metric(
        observed_freq: dict,
        expected_freq: dict,
        ) -> float:
    """
    Calculate the ligation bias metric from the output of
    the ligation_bias_distribution module.

    This metric is the K-L divergence of the ligation bias distribution
    of the observed frequencies from the expected frequencies. The
    expected frequencies are calculated from the nucleotide composition
    of the genome.

    Inputs:
        observed_freq: Dictionary containing the output of the
                ligation_bias_distribution module
        expected_freq: Dictionary containing the expected frequencies

    Outputs:
        lbd_df: Dataframe containing the ligation bias metric in bits
    """
    kl_divergence = 0.0

    for dinucleotide, observed_prob in observed_freq.items():
        expected_prob = expected_freq[dinucleotide]
        kl_divergence += observed_prob * math.log2(
                                            observed_prob / expected_prob
                                            )

    return kl_divergence


def calculate_score(probabilities):
    '''
    Calculate the triplet periocity score for a given probability of a read
    being in frame. The score is the square root of the bits of information in
    the triplet distribution.

    Numerator is the Maximum Entropy of the triplet distribution minus the
    entropy of the triplet distribution.
    Denominator is the Maximum Entropy of the triplet distribution.

    Inputs:
        probability (float): The probability of a read being in frame.

    Returns:
        result (float): The triplet periodicity score.
    '''
    maximum_entropy = math.log2(3)
    entropy = 0
    for probability in probabilities:
        entropy += -(probability * math.log2(probability))

    result = math.sqrt((maximum_entropy - entropy) / maximum_entropy)
    return result


def read_frame_distribution_information_content_metric(
    read_frame_distribution: dict,
        ) -> float:
    """
    Calculate the read frame distribution metric from the output of
    the read_frame_distribution module.

    This metric is the Shannon entropy of the read frame distribution

    Inputs:
        read_frame_distribution: Dictionary containing the output of the
                read_frame_distribution module

    Outputs:
        read_frame_distribution_metric: Shannon entropy of the read frame
                distribution
    """
    pseudocount = 1e-100
    pre_scores = {}
    for read_length in read_frame_distribution:
        total_count = sum(read_frame_distribution[read_length].values())

        probabilities = []
        for frame, count in read_frame_distribution[read_length].items():
            prob = (count + pseudocount) / total_count
            probabilities.append(prob)

        score = calculate_score(probabilities)

        pre_scores[read_length] = score, total_count

    return pre_scores


def information_metric_cutoff(
    pre_scores: dict,
    min_count_threshold: float = 0.05,
        ) -> dict:
    """
    Apply the cut off to the information content metric

    Inputs:
        pre_scores: Dictionary containing the output of the
                read_frame_distribution_information_content_metric module
        min_count_threshold: Minimum count threshold for a read length to be
                included in the metric

    Outputs:
        information_content_metric: Dictionary containing the information
                content metric for each read length
    """
    information_content_metric = {}
    total_reads = sum(
        pre_scores[key][1]
        for key in pre_scores
        )
    for read_length in pre_scores:
        score, count = pre_scores[read_length]
        print(count, total_reads * min_count_threshold)
        if count > total_reads * min_count_threshold:
            information_content_metric[read_length] = score
    return information_content_metric


def triplet_periodicity_best_read_length_score(information_content_metric):
    '''
    Produce a single metric for the triplet periodicity by taking the maximum
    score across all read lengths.

    Inputs:
        information_content_metric (dict): The information content metric
            for each read length.

    Returns:
        result (float): The triplet periodicity score.
    '''
    return max(information_content_metric.values())


def triplet_periodicity_weighted_score(
    information_content_metric,
    read_length_distribution,
        ):
    '''
    Produce a single metric for the triplet periodicity by taking the weighted
    average of the scores for each read length.

    Inputs:
        information_content_metric (dict): The information content metric
            for each read length.
        read_length_distribution_metric (float): The read length distribution.

    Returns:
        result (float): The triplet periodicity score.
    '''
    total_reads = sum(
        read_length_distribution[key][nested_key]
        for key in read_length_distribution
        for nested_key in read_length_distribution[key]
        )
    weighted_scores = []
    for read_length, score in information_content_metric.items():
        weighted_score = score * sum(
            read_length_distribution[read_length].values()
            )
        weighted_scores.append(weighted_score)

    return sum(weighted_scores) / total_reads


def triplet_periodicity_weighted_score_best_3_read_lengths(
        pre_scores: dict,) -> float:
    """
    Produce a single metric for the triplet periodicity by taking the weighted
    average of the scores for the best 3 read lengths.

    Inputs:
        pre_scores: Dictionary containing the information
                content metric and total counts for each read length

    Returns:
        result: The triplet periodicity score
    """
    total_reads = sum(
        pre_scores[key][1]
        for key in pre_scores
        )
    weighted_scores = []
    for _, score in pre_scores.items():
        weighted_score = score[0] * score[1]
        weighted_scores.append(weighted_score)

    return sum(weighted_scores) / total_reads
