"""
Configuração central: mapa de documentos lógicos → arquivos PDF.
Um documento lógico pode ter 1+ PDFs (multipartes) e ser do tipo:
  - ACT        (Acordo Coletivo de Trabalho)
  - DC         (Dissídio Coletivo)
  - DCG        (Dissídio Coletivo de Greve)
  - Cartilha   (material de divulgação, não normativo)
  - ADITAMENTO (anexa-se ao documento base, não gera JSON próprio)
"""

ANO_MIN = 1988
ANO_MAX = 2026

DOCUMENTOS = {
    # ---------------- 1988–1993 ----------------
    "1988": {
        "arquivos": ["Acordo-Coletivo-1988_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1989": {
        "arquivos": ["Acordo-Coletivo-1989.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1990": {
        "arquivos": ["Acordo-Coletivo-1990_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1990-suplementar": {
        "arquivos": ["Acordo-Coletivo-1990-Suplementar.pdf"],
        "tipo": "ADITAMENTO", "base": "1990",
    },
    "1991": {
        "arquivos": ["Acordo-Coletivo-1991-parcial.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
        "observacao": "Acordo parcial homologado no TST",
    },
    "1992": {
        "arquivos": ["Acordo-Coletivo-1992_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1993": {
        "arquivos": ["Acordo-Coletivo-1993_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },

    # ---------------- 1994–1999 ----------------
    "1994-1995": {
        "arquivos": ["Acordo-coletivo-1994-1995.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1995-1996": {
        "arquivos": ["Acordo-Coletivo-1995-1996.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1995-1996-aditamento": {
        "arquivos": ["Acordo-Coletivo-1995-1996-Aditamento.pdf"],
        "tipo": "ADITAMENTO", "base": "1995-1996",
    },
    "1997-1998": {
        "arquivos": ["Acordo-Coletivo-1997-1998.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1998-1999": {
        "arquivos": ["Acordo-Coletivo-1998-1999.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "1999-2000": {
        "arquivos": ["Acordo-Coletivo-1999-2000.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },

    # ---------------- 2000–2005 ----------------
    "2000-2001": {
        "arquivos": ["Acordo-Coletivo-2000-2001.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
        "observacao": "Homologado no TST como DC",
    },
    "2001-2002": {
        "arquivos": [
            "Acordo-Coletivo-2001-2002_redP1.pdf",
            "Acordo-Coletivo-2001-2002_redp2.pdf",
        ],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2002-2003": {
        "arquivos": ["Acordo-Coletivo-2002-2003.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2003-2004": {
        "arquivos": [
            "Acordo-Coletivo-2003-2004_redP1.pdf",
            "Acordo-Coletivo-2003-2004_redp2.pdf",
            "Acordo-Coletivo-2003-2004_redp3.pdf",
        ],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2004-2005": {
        "arquivos": [
            "Acordo-Coletivo-2004-2005_P1.pdf",
            "Acordo-Coletivo-2004-2005_p2.pdf",
            "Acordo-Coletivo-2004-2005_p3.pdf",
        ],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2005-2006": {
        "arquivos": ["Acordo-Coletivo-2005-2006_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
        "greve": {"ocorreu": True, "periodo": "setembro/2005"},
    },

    # ---------------- 2007–2011 ----------------
    "2007-2008": {
        "arquivos": [
            "Acordo-Coletivo-2007-2008_redp1.pdf",
            "Acordo-Coletivo-2007-2008_redp2.pdf",
        ],
        "tipo": "ACT", "entidades": ["FENTECT"],
        "greve": {"ocorreu": True, "periodo": "2007"},
    },
    "2008-2009": {
        "arquivos": ["Acordo-Coletivo-2008-2009-Minuta-do-ACT-2008-2009_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2008-2009-complem-13-10": {
        "arquivos": ["Acordo-Coletivo-2008-2009-Complem-Ata-do-dia-13.10.2008.pdf"],
        "tipo": "ADITAMENTO", "base": "2008-2009",
    },
    "2008-2009-complem-14-10": {
        "arquivos": ["Acordo-Coletivo-2008-2009-Complem-Ata-do-dia-14.10.2008.pdf"],
        "tipo": "ADITAMENTO", "base": "2008-2009",
    },
    "2009-2011": {
        "arquivos": [
            "Acordo-Coletivo-2009-2011_redp1.pdf",
            "Acordo-Coletivo-2009-2011_redp2.pdf",
        ],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },

    # ---------------- 2011–2019 ----------------
    "2011-2012": {
        "arquivos": ["Acordo-Coletivo-2011-2012-Acórdão-TST-DC-6335-37-2011-5-00-0000.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
    },
    "2012-2013": {
        "arquivos": ["Acordo-Coletivo-2012-2013-Acórdão-TST-DC-8981-76-2012-5-00-0000.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
    },
    "2013-2014-fentect": {
        "arquivos": ["Acordo-Coletivo-2013-2014-Acórdão-TST-DC-6942-72-2013-5-00-0000.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
        "grupo": "2013-2014", "papel": "FENTECT",
    },
    "2013-2014-findect": {
        "arquivos": ["Acordo-Coletivo-2013-2014-FINDECT_red.pdf"],
        "tipo": "ACT", "entidades": ["FINDECT"],
        "grupo": "2013-2014", "papel": "FINDECT",
    },
    "2014-2015": {
        "arquivos": ["Acordo-Coletivo-2014-2015_red.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2015-2016": {
        "arquivos": ["ACT-2015-2016-Assinado-no-TST-Gabriel-2.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2016-2017": {
        "arquivos": ["ACT-2016-2017-Assinado.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2017-2018": {
        "arquivos": ["LIVRETO-ACT-2017-2018.pdf"],
        "tipo": "Cartilha", "entidades": ["FENTECT"],
        "observacao": "Livreto de divulgação — pode não conter todas as cláusulas",
    },
    "2018-2019": {
        "arquivos": ["ACT-2018-2019-A5.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },

    # ---------------- 2019–2022 (três documentos) ----------------
    "2019-2021": {
        "arquivos": ["Acordao-2019-2021.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
    },
    "2020-2021": {
        "arquivos": ["Acordao-2020-2021.pdf"],
        "tipo": "DC", "entidades": ["FENTECT"],
    },
    "2021-2022": {
        "arquivos": ["Acordao_2021-2022.pdf"],
        "tipo": "DCG", "entidades": ["FENTECT", "FINDECT"],
        "greve": {"ocorreu": True, "periodo": "17/08/2021"},
    },

    # ---------------- 2022–2026 ----------------
    "2022-2023": {
        "arquivos": ["ACT-2022-2023.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
    },
    "2023-2024": {
        "arquivos": ["ACT-2023-2024.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT", "FINDECT"],
    },
    "2023-2024-aditivo": {
        "arquivos": ["1__Termo_Aditivo_ACT_2023_2024.pdf"],
        "tipo": "ADITAMENTO", "base": "2023-2024",
    },
    "2024-2025-fentect": {
        "arquivos": ["ACT-2024-2025-FENTECT.pdf"],
        "tipo": "ACT", "entidades": ["FENTECT"],
        "grupo": "2024-2025", "papel": "FENTECT",
    },
    "2024-2025-findect": {
        "arquivos": ["ACT-2024-2025-FINDECT.pdf"],
        "tipo": "ACT", "entidades": ["FINDECT"],
        "grupo": "2024-2025", "papel": "FINDECT",
    },
    "2025-2026": {
        "arquivos": ["Acordao-DC-1001307-73.2025.5.00.0000-1.pdf"],
        "tipo": "DCG", "entidades": ["FENTECT", "FINDECT"],
    },
}