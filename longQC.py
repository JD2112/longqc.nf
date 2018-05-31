'''
   Author: Yoshinori Fukasawa, Bioscience Core Lab @ KAUST, KSA

   Project Name: longQC.py
   Start Date: 2017-10-10
   Version: 0.1

   Usage:
      longQC.py [options]

      Try 'longQC.py -h' for more information.

    Purpose: longQC enables you to asses quality of sequence data
             coming from third-generation sequencers (long read).

    Bugs: Please contact yoshinori.fukasawa@kaust.edu.sa
'''

import sys, os, logging, json, argparse, shlex
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import numpy             as np
import pandas as pd
from time        import sleep
from scipy.stats import gamma
from jinja2      import Environment, FileSystemLoader

import lq_nanopore
import lq_rs
import lq_sequel

from lq_gamma    import estimate_gamma_dist_scipy
from lq_utils    import open_seq, get_N50, rgb, sample_random_fastq_list, write_fastq, get_Qx_bases, copytree
from lq_adapt    import cut_adapter
from lq_gcfrac   import plot_unmasked_gc_frac
from lq_exec     import LqExec
from lq_coverage import LqCoverage
from lq_mask     import LqMask

def command_run(args):
    if args.suf:
        suf = args.suf
    else:
        suf = None
    if args.platform == 'rs2':
        lq_rs.run_platformqc(args.raw_data_dir, args.out, suffix=suf)
    elif args.platform == 'sequel':
        lq_sequel.run_platformqc(args.raw_data_dir, args.out, suffix=suf)
    elif args.platform == 'minion':
        lq_nanopore.run_platformqc(args.platform, args.raw_data_dir, args.out, suffix=suf, n_channel=512)
    elif args.platform == 'gridion':
        lq_nanopore.run_platformqc(args.platform, args.raw_data_dir, args.out, suffix=suf, n_channel=512)
    else:
        pass

def command_help(args):
    print(parser.parse_args([args.command, '--help']))

def plot_length_dist(fig_path, lengths, g_a, g_b, _max, _mean, _n50, isPb=False, b_width = 1000):
    x = np.linspace(0, gamma.ppf(0.99, g_a, 0, g_b))
    est_dist = gamma(g_a, 0, g_b)
    plt.hist(lengths, histtype='step', bins=np.arange(min(lengths),_max + b_width, b_width), color=rgb(214,39,40), alpha=0.7, normed=True)
    plt.grid(True)
    plt.xlabel('Read length')
    plt.ylabel('Probability density')
    plt.axvline(x=_mean, linestyle='dashed', linewidth=2, color=rgb(214,39,40), alpha=0.8)
    plt.axvline(x=_n50,  linewidth=2, color=rgb(214,39,40), alpha=0.8)
    plt.xlim(0, gamma.ppf(0.99, g_a, 0, g_b))

    ymin, ymax = plt.gca().get_ylim()
    xmin, xmax = plt.gca().get_xlim()

    if not isPb:
        plt.text(xmax*0.6, ymax*0.72, r'$\alpha=%.3f,\ \beta=%.3f$' % (g_a, g_b) )
        plt.text(xmax*0.6, ymax*0.77,  r'Gamma dist params:' )
        plt.plot(x, est_dist.pdf(x), color=rgb(214,39,40) )

    plt.text(xmax*0.6, ymax*0.85, r'sample mean: %.3f' % (_mean,) )
    plt.text(xmax*0.6, ymax*0.9, r'N50: %.3f' % (_n50,) )

    plt.text(_mean, ymax*0.85, r'Mean', color=rgb(214,39,40))
    plt.text(_n50, ymax*0.9, r'N50', color=rgb(214,39,40))

    plt.axis('tight')
    plt.xlim(0, gamma.ppf(0.99, g_a, 0, g_b))
    plt.savefig(fig_path, bbox_inches="tight")
    #plt.show()
    plt.close()

def plot_qscore_dist(df, column_qv, column_length, *, fp=None, platform='ont', interval=3000):
    if platform == 'ont':
        mid_threshold = 7 # ont
    else:
        mid_threshold = 8 # pb
    df['Interval'] = np.floor(df[column_length].values/interval)
    df.boxplot(column=column_qv, by='Interval', sym='+', rot=90, figsize=(2*int(max(df['Interval'])/5+0.5), 4.8))
    plt.grid(True)
    xmin, xmax = plt.gca().get_xlim()
    ymin, ymax = plt.gca().get_ylim()
    plt.xticks(np.arange(xmax+1), [int(i) for i in np.arange(xmax+1)*interval])
    plt.axhspan(0,  5, facecolor='red', alpha=0.1)
    plt.axhspan(5,  mid_threshold, facecolor='yellow', alpha=0.1)
    plt.axhspan(mid_threshold, ymax, facecolor='green', alpha=0.1)
    #plt.boxplot(df[5].values[np.where(df[4] == 0.0)])
    plt.ylim(0, ymax)
    plt.ylabel('Averaged QV')
    plt.title("")
    plt.suptitle("")
    if fp:
        plt.savefig(fp, bbox_inches="tight")
    else:
        plt.show()
    plt.close()

def main(args):
    if hasattr(args, 'handler'):
        args.handler(args)
    else:
        parser.printhelp()

def command_sample(args):
    if args.suf:
        suffix = "_" + args.suf
    else:
        suffix = ""

    cov_path    = os.path.join(args.out, "analysis", "minimap2", "coverage_out" + suffix + ".txt")
    cov_path_e  = os.path.join(args.out, "analysis", "minimap2", "coverage_err" + suffix + ".txt")
    sample_path = os.path.join(args.out, "analysis", "subsample" + suffix + ".fastq")
    log_path    = os.path.join(args.out, "logs", "log_longQC_sampleqc" + suffix + ".txt")
    fig_path    = os.path.join(args.out, "figs", "fig_longQC_sampleqc_length" + suffix + ".png")
    fig_path_rq = os.path.join(args.out, "figs", "fig_longQC_sampleqc_average_qv" + suffix + ".png")
    fig_path_ma = os.path.join(args.out, "figs", "fig_longQC_sampleqc_masked_region" + suffix + ".png")
    fig_path_gc = os.path.join(args.out, "figs", "fig_longQC_sampleqc_gcfrac" + suffix + ".png")
    fig_path_cv = os.path.join(args.out, "figs", "fig_longQC_sampleqc_coverage" + suffix + ".png")
    fig_path_qv = os.path.join(args.out, "figs", "fig_longQC_sampleqc_olp_qv" + suffix + ".png")
    fig_path_ta = os.path.join(args.out, "figs", "fig_longQC_sampleqc_terminal_analysis" + suffix + ".png")
    fig_path_cl = os.path.join(args.out, "figs", "fig_longQC_sampleqc_coverage_over_read_length" + suffix + ".png")
    json_path   = os.path.join(args.out, "QC_vals_longQC_sampleqc" + suffix + ".json")
    fastx_path  = ""
    html_path   = os.path.join(args.out, "web_summary" + suffix + ".html")

    df_mask = None
    tuple_5 = tuple_3 = None

    # output_path will be made too.
    if not os.path.isdir(os.path.join(args.out, "analysis", "minimap2")):
        os.makedirs(os.path.join(args.out, "analysis", "minimap2"), exist_ok=True)

    if not os.path.isdir(os.path.join(args.out, "logs")):
        os.makedirs(os.path.join(args.out, "logs"), exist_ok=True)

    if not os.path.isdir(os.path.join(args.out, "figs")):
        os.makedirs(os.path.join(args.out, "figs"), exist_ok=True)

    ### logging conf ###
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_path, 'w')
    sh = logging.StreamHandler()

    formatter = logging.Formatter('%(module)s:%(asctime)s:%(lineno)d:%(levelname)s:%(message)s')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)

    logger.addHandler(sh)
    logger.addHandler(fh)
    #####################

    if args.preset:
        p = args.preset
        if p == 'rs2':
            args.pb = True
            args.adp5 = "ATCTCTCTCTTTTCCTCCTCCTCCGTTGTTGTTGTTGAGAGAGAT"
            args.adp3 = "ATCTCTCTCTTTTCCTCCTCCTCCGTTGTTGTTGTTGAGAGAGAT"
            args.miniargs = "-Y -k 12 -w 5 -l 0"
        elif p == 'sequel':
            args.pb = True
            args.adp5 = "ATCTCTCTCAACAACAACAACGGAGGAGGAGGAAAAGAGAGAGAT"
            args.adp3 = "ATCTCTCTCAACAACAACAACGGAGGAGGAGGAAAAGAGAGAGAT"
            args.miniargs = "-Y -k 12 -w 5 -l 0 -q 140"
        elif p == 'ont-ligation':
            args.ont = True
            args.adp5 = "AATGTACTTCGTTCAGTTACGTATTGCT"
            args.adp3 = "GCAATACGTAACTGAACGAAGT"
            args.miniargs = "-Y -k 12 -w 5 -l 1000"
        elif p == 'ont-rapid':
            args.ont = True
            args.adp5 = "GTTTTCGCATTTATCGTGAAACGCTTTCGCGTTTTTCGTGCGCCGCTTCA"
            args.miniargs = "-Y -k 12 -w 5 -l 1000"
        elif p == 'ont-1dsq':
            args.ont = True
            args.adp5 = "GGCGTCTGCTTGGGTGTTTAACCTTTTTGTCAGAGAGGTTCCAAGTCAGAGAGGTTCCT"
            args.adp3 = "GGAACCTCTCTGACTTGGAACCTCTCTGACAAAAAGGTTAAACACCCAAGCAGACGCCAGCAAT"
            args.miniargs = "-Y -k 12 -w 5 -l 1000"
        logger.info("Preset \"%s\" was applied. Options --pb(--ont), --adapter_[53], --minimap2_args were overwritten." % (p,))

    (file_format_code, reads, n_seqs, n_bases) = open_seq(args.input)
    logger.info('Input file parsing was finished. #seqs:%d, #bases: %d' % (n_seqs, n_bases))
    if file_format_code == 0:
        fastx_path = os.path.join(args.out, "analysis", "pbbam_converted_seq_file" + suffix + ".fastq")
        write_fastq(fastx_path, reads)
        logger.info('Temporary work file was made at %s' % fastx_path)
    elif file_format_code == -1 or file_format_code == 1:
        logger.error('Input file is unsupported file format: %s' % args.input)
        sys.exit()
    else:
        fastx_path = args.input

    logger.info("Computation of the low complexity region started.")
    lm = LqMask(reads, "/home/fukasay/Projects/minimap2_mod/sdust", args.out, suffix=suffix, n_proc=10)
    lm.run_async_sdust()
    logger.info("Summary table %s was made." % lm.get_outfile_path())
    lm.plot_masked_fraction(fig_path_ma)

    # list up seqs should be avoided
    df_mask      = pd.read_table(lm.get_outfile_path(), sep='\t', header=None)
    exclude_seqs = df_mask[(df_mask[2] > 500000) & (df_mask[3] > 0.2)][0].values.tolist() # len > 0.5M and mask_region > 20%. k = 15
    exclude_seqs = exclude_seqs + df_mask[(df_mask[2] > 20000) & (df_mask[3] > 0.4)][0].values.tolist() # len > 0.02M and mask_region > 40%. k = 12. more severe.
    logger.debug("Highly masked seq list:\n%s" % "\n".join(exclude_seqs) )
    (sreads, s_n_seqs, s_n_bases) = sample_random_fastq_list(reads, args.nsample, elist=exclude_seqs)
    logger.info('sequence sampling finished. #seqs:%d, #bases: %d, #n_sample: %f' % (s_n_seqs, s_n_bases, float(args.nsample)))
    write_fastq(sample_path, sreads)

    q10 = np.sum(df_mask[5].values) # make c code to compute Q10 now for speed
    #q10 =  get_Qx_bases(reads, threshold=10) # too slow
    logger.info("Q%d bases %d" % (10, q10))

    plot_qscore_dist(df_mask, 4, 2, fp=fig_path_rq)

    # asynchronized
    le = LqExec("/home/fukasay/Projects/minimap2_mod/minimap2-coverage", logger=logger)
    le_args = shlex.split("%s -t %d %s %s" % (args.miniargs, int(args.minit), fastx_path, sample_path))
    le.exec(*le_args, out=cov_path, err=cov_path_e)

    logger.info("Overlap computation started. Process is %s" % le.get_pid())

    if df_mask is not None:
        lengths = df_mask[2].values
    else:
        lengths = []
    tobe_json = {}

    if len(lengths) == 0:
        lengths = [len(r[1]) for r in reads]

    # length distribution. a ~= 1.0 is usual (exponential dist).
    (a, b) = estimate_gamma_dist_scipy(lengths, logger)
    
    throughput = np.sum(lengths)
    longest    = np.max(lengths)
    mean_len   = np.array(lengths).mean()
    n50        = get_N50(lengths)

    logger.info("Throughput: %d" % throughput)
    logger.info("Length of longest read: %d" % longest)
    logger.info("The number of reads: %d", len(lengths))

    tobe_json["Yield"]            = int(throughput)
    tobe_json["Q10 bases"]        = str("%.2f%%" % float(100*q10/throughput))
    tobe_json["Longest_read"]     = int(longest)
    tobe_json["Num_of_reads"]     = len(lengths)
    tobe_json["Length_stats"] = {}
    tobe_json["Length_stats"]["gamma_params"]     = [float(a), float(b)]
    tobe_json["Length_stats"]["Mean_read_length"] = float(mean_len)
    tobe_json["Length_stats"]["N50_read_length"]  = float(n50)

    plot_length_dist(fig_path, lengths, a, b, longest, mean_len, n50, True if args.pb else False)
    logger.info("Genarated the sample read length plot.")

    (gc_read_mean, gc_read_sd) = plot_unmasked_gc_frac(reads, logger=logger, fp=fig_path_gc)
    logger.info("Genarated the sample gc fraction plot.")

    tobe_json["GC_stats"] = {}
    tobe_json["GC_stats"]["Mean_GC_content"] = gc_read_mean
    tobe_json["GC_stats"]["SD_GC_content"]   = gc_read_sd

    if args.adp5 and args.adp3:
        (tuple_5, tuple_3) = cut_adapter(reads, adp_t=args.adp5, adp_b=args.adp3, logger=logger)
    elif not args.adp5 and args.adp3:
        tuple_3 = cut_adapter(reads, adp_b=args.adp3, adp_t=None, logger=logger)
        #cut_adapter(reads, lengths, adp3, logger=logger)
    elif args.adp5 and not args.adp3:
        tuple_5 = cut_adapter(reads, adp_t=args.adp5, adp_b=None, logger=logger)

    if tuple_5:
        tobe_json["Stats_for_adapter5"] = {}
        tobe_json["Stats_for_adapter5"]["Num_of_trimmed_reads_5"] = tuple_5[1]
        tobe_json["Stats_for_adapter5"]["Max_identity_adp5"] = tuple_5[0]
        tobe_json["Stats_for_adapter5"]["Average_position_from_5_end"] = np.mean(tuple_5[2])

    if tuple_3:
        tobe_json["Stats_for_adapter3"] = {}
        tobe_json["Stats_for_adapter3"]["Num_of_trimmed_reads_3"] = tuple_3[1]
        tobe_json["Stats_for_adapter3"]["Max_identity_adp3"] = tuple_3[0]
        tobe_json["Stats_for_adapter3"]["Average_position_from_3_end"] = np.mean(tuple_3[2])

    # trimmed reads by edlib are saved as fastq
    if args.trim:
        write_fastq(args.trim, reads)

    # here wait until the minimap procerss finishes
    while True:
        if le.get_poll() is not None:
            logger.info("Process %s for %s terminated." % (le.get_pid(), le.get_bin_path()))
            break
        logger.info("Calculating overlaps of sampled reads...")
        sleep(30)

    logger.info("Overlap computation finished.")

    # execute minimap2_coverage
    logger.info("Generating coverage related plots...")
    lc = LqCoverage(cov_path, logger)
    lc.plot_coverage_dist(fig_path_cv)
    lc.plot_unmapped_frac_terminal(fig_path_ta, adp5_pos=len(args.adp5) if args.adp5 else None, adp3_pos=len(args.adp3) if args.adp3 else None)
    lc.plot_qscore_dist(fig_path_qv)
    lc.plot_length_vs_coverage(fig_path_cl)
    logger.info("Generated coverage related plots.")

    tobe_json["Coverage_stats"] = {}
    tobe_json["Coverage_stats"]["Non-overlapped fraction"] = float(lc.get_unmapped_frac())
    tobe_json["Coverage_stats"]["Mean_coverage"] = float(lc.get_mean())
    tobe_json["Coverage_stats"]["SD_coverage"]   = float(lc.get_sd())
    tobe_json["Coverage_stats"]["Estimated_crude_ome_size"] = str(lc.calc_genome_size(throughput))
    if args.preset:
        if args.preset == 'sequel':
            tobe_json["Coverage_stats"]["Low quality read fraction"] = float(lc.get_unmapped_bad_frac() - lc.get_unmapped_frac())

    with open(json_path, "w") as f:
        logger.info("Quality measurements were written into a JSON file: %s" % json_path)
        json.dump(tobe_json, f, indent=4)

    logger.info("Generated a json summary.")

    root_dict = {}
    root_dict['stats']  = {'Sample name': suffix.replace('_', ''), 'Yield': int(throughput), 'Longest read': int(longest), \
                           'Number of reads': len(lengths), 'Q10 bases': "%.3f%%" % float(100*q10/throughput) }
    if lc.get_unmapped_frac():
        root_dict['stats']['Non-overlapped read fraction'] = "%.3f" % float(lc.get_unmapped_frac())

    if args.preset:
        if args.preset == 'sequel':
            root_dict['stats']["Low quality read fraction"] = float(lc.get_unmapped_bad_frac() - lc.get_unmapped_frac())

    if tuple_5 or tuple_3:
        root_dict['ad'] = {}
    if tuple_5:
        root_dict['ad']["Number of trimmed reads in 5\'"] = tuple_5[1]
        root_dict['ad']["Max seq identity for the adpter in 5\'"] = "%.3f" % tuple_5[0]
        root_dict['ad']["Average trimmed length in 5\'"] = "%.3f" % np.mean(tuple_5[2])
    if tuple_3:
        root_dict['ad']["Number of trimmed reads in 3\'"] = tuple_3[1]
        root_dict['ad']["Max seq identity for the adpter in 3\'"] = "%.3f" % tuple_3[0]
        root_dict['ad']["Average trimmed length in 3\'"] = "%.3f" % np.mean(tuple_3[2])

    root_dict['rl'] = {'name': os.path.basename(fig_path),\
                      'stats':{\
                               'Mean read length': "%.3f" % mean_len,\
                               'N50': "%.3f" % n50
                      }}
    root_dict['rq'] = {'name': os.path.basename(fig_path_rq)}
    root_dict['rc'] = {'cov_plot_name': os.path.basename(fig_path_cv), 'cov_over_len_plot_name': os.path.basename(fig_path_cl),\
                       'cov_ovlp_qv_plot_name': os.path.basename(fig_path_qv),\
                       'stats':{\
                                'Number of sampled reads':s_n_seqs,\
                                'Mean per read coverage': "%.3f" % lc.get_mean(),\
                                's.d. per read coverage': "%.3f" % lc.get_sd(), \
                                'Crude estimated ome size': lc.calc_genome_size(throughput),\
                        }}
    root_dict['gc'] = {'name': os.path.basename(fig_path_gc),\
                      'stats':{\
                               'Mean per read GC content': "%.3f %%" % (100.0 * gc_read_mean),\
                               's.d. per read GC content': "%.3f %%" % (100.0 * gc_read_sd)
                      }}
    root_dict['fr'] = {'name': os.path.basename(fig_path_ta)}
    root_dict['sc'] = {'name': os.path.basename(fig_path_ma)}

    env = Environment(loader=FileSystemLoader('./', encoding='utf8'))
    tpl = env.get_template('./web_summary/web_summary.tpl.html')
    html = tpl.render( root_dict )
    with open(html_path, "wb") as f:
        f.write(html.encode('utf-8'))
    if not os.path.isdir(os.path.join(args.out, "css")):
        os.makedirs(os.path.join(args.out, "css"), exist_ok=True)
    if not os.path.isdir(os.path.join(args.out, "vendor")):
        os.makedirs(os.path.join(args.out, "vendor"), exist_ok=True)
    if not os.path.isdir(os.path.join(args.out, "figs")):
        os.makedirs(os.path.join(args.out, "figs"), exist_ok=True)
    copytree('./web_summary/css', os.path.join(args.out, "css"))
    copytree('./web_summary/vendor', os.path.join(args.out, "vendor"))
    copytree('./web_summary/figs', os.path.join(args.out, "figs"))
    logger.info("Generated a summary html.")

    logger.info("Finished all processes.")

# stand alone
if __name__ == "__main__":
    # parsing
    parser = argparse.ArgumentParser(
        prog='LongQC.py',
        description='LongQC is a software to asses the quality of long read data from the third generation sequencers.',
        add_help=True,
    )
    subparsers = parser.add_subparsers()

    # run qc
    platforms = ["rs2", "sequel", "minion", "gridion"]
    parser_run = subparsers.add_parser('runqc', help='see `runqc -h`')
    parser_run.add_argument('-s', '--suffix', help='suffix for each output file.', dest = 'suf', default = None)
    parser_run.add_argument('-o', '--output', help='path for output directory', dest = 'out', default = None)
    parser_run.add_argument('platform', choices=platforms, help='a platform to be evaluated. ['+", ".join(platforms)+']', metavar='platform')
    parser_run.add_argument('raw_data_dir', type=str, help='a path for a dir containing the raw data')
    #parser_run.add_argument('--rs', help='asseses a run of PacBio RS-II', dest = 'pbrs', action = 'store_true', default = None)
    #parser_run.add_argument('--sequel', help='asseses a run of PacBio Sequel', dest = 'pbsequel', choices=['kit2', 'kit2.1'], default = None)
    #parser_run.add_argument('--minion', help='asseses a run of ONT MinION', dest = 'ontmin', action = 'store_true', default = None)
    #parser_run.add_argument('--gridion', help='asseses a run of ONT GridION', dest = 'ontgrid', action = 'store_true', default = None)
    #parser_sample.add_argument('--promethion', help='asseses a run of ONT PromethION', dest = 'ontprom', action = 'store_true', default = None)
    parser_run.set_defaults(handler=command_run)

    # run sample
    presets = ["rs2", "sequel", "ont-ligation", "ont-rapid", "ont-1dsq"]
    help_preset = 'a platform/kit to be evaluated. adapter and some ovlp parameters are automatically applied. ['+", ".join(presets)+'].'
    parser_sample = subparsers.add_parser('sampleqc', help='see `sampleqc -h`')
    parser_sample.add_argument('--pb', help='sample data from PacBio sequencers', dest = 'pb', action = 'store_true', default = None)
    parser_sample.add_argument('--ont', help='sample data from ONT sequencers', dest = 'ont', action = 'store_true', default = None)
    parser_sample.add_argument('--adapter_5', help='adapter sequence for 5\'', dest = 'adp5', default = None)
    parser_sample.add_argument('--adapter_3', help='adapter sequence for 3\'', dest = 'adp3', default = None)
    parser_sample.add_argument('--n_sample', help='the number/fraction of sequences for sampling.', type=int, dest = 'nsample', default = 10000)
    parser_sample.add_argument('--minimap2_args', help='the arguments for minimap2.', dest = 'miniargs', default = '-Y -k 12 -w 5')
    parser_sample.add_argument('--minimap2_thread', help='the number of threads for sequences for minimap2.', dest = 'minit', default = 50)
    parser_sample.add_argument('-p', '--preset', choices=presets, help=help_preset, metavar='preset')
    parser_sample.add_argument('-s', '--sample_name', help='sample name is added as a suffix for each output file.', dest = 'suf', default = None)
    parser_sample.add_argument('-o', '--output', help='path for output directory', dest = 'out', required=True, default = None)
    parser_sample.add_argument('-t', '--trim_output', help='path for trimmed reads. If this is None, trimmed reads won\'t be saved.', dest = 'trim', default = None)
    parser_sample.add_argument('input', help='Input [fasta, fastq, or pbbam]', type=str)
    parser_sample.set_defaults(handler=command_sample)

    # help
    parser_help = subparsers.add_parser('help', help='see `help -h`')
    parser_help.add_argument('command', help='')
    parser_help.set_defaults(handler=command_help)

    args = parser.parse_args()
    main(args)
