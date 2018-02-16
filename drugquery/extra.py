# auxilliary DrugQuery functions

# returns the tanimoto coefficient btw. two molecules
def tanimoto(cpd1, cpd2):
    return cpd1.calcfp() | cpd2.calcfp()

# returns compounds that are structurally similar to the query molecule above a specified cutoff
# FIRST input (query_mol) must be a pybel mol object
# SECOND input ref_cpds must be a list of Compound objects
def get_similar_cpds(query_mol, ref_cpds):
    similarity_cutoff = 0.3  # min tanimoto coefficient for 'similar' compounds
    similar_cpds = []
    for cpd in ref_cpds:
        ref_mol = cpd.get_pybel_mol()
        tan = tanimoto(query_mol, ref_mol)
        if tan >= similarity_cutoff:
            similar_cpds.append((cpd, tan))
    return similar_cpds
