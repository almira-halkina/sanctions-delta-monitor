window.RPCM_DATA = {
 "built": "2026-10-09",
 "affiliates_rule_reimposition": "2026-11-10",
 "regimes": {
  "ofac_50pct": {
   "name": "OFAC 50 Percent Rule",
   "citation": "OFAC Revised Guidance on Entities Owned by Blocked Persons, 13 Aug 2014",
   "threshold": 50.0,
   "comparator": "≥",
   "seed_sources": [
    "ofac_sdn"
   ],
   "control_test": false,
   "aggregate": true,
   "note": "In force."
  },
  "bis_affiliates": {
   "name": "BIS Affiliates Rule",
   "citation": "90 FR 47254 (29 Sep 2025); suspension 90 FR 52099 (12 Nov 2025)",
   "threshold": 50.0,
   "comparator": "≥",
   "seed_sources": [
    "bis_csl",
    "ofac_sdn"
   ],
   "control_test": false,
   "aggregate": true,
   "note": "Suspended to 9 Nov 2026; reimposed 10 Nov 2026 absent further action."
  },
  "eu_ownership_control": {
   "name": "EU ownership or control",
   "citation": "Council Best Practices 8519/18, paras 62-63",
   "threshold": 50.0,
   "comparator": ">",
   "seed_sources": [
    "eu_fsd"
   ],
   "control_test": true,
   "aggregate": true,
   "note": "In force."
  }
 },
 "demo": {
  "as_of": "2026-08-04",
  "previous": "2026-08-03",
  "deltas": [
   {
    "key": "bis:fee27a089fb2be6c",
    "source": "bis_csl",
    "change_type": "added",
    "name": "KASPIY PRECISION MACHINING LLP",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [],
    "field_changes": [],
    "event_type": "new_designation",
    "authorities": [
     "US/BIS Entity List",
     "unclassified"
    ],
    "jurisdictions": [
     "KZ"
    ],
    "jurisdiction_names": [
     "Kazakhstan"
    ],
    "high_opacity": true,
    "rationale": "key absent from prior publication",
    "priority": 0,
    "row_count_visible": true
   },
   {
    "key": "eu:88417",
    "source": "eu_fsd",
    "change_type": "added",
    "name": "OAO NEMIGA OPTICS",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [],
    "field_changes": [],
    "event_type": "new_designation",
    "authorities": [
     "US/OFAC Belarus"
    ],
    "jurisdictions": [
     "BY"
    ],
    "jurisdiction_names": [
     "Belarus"
    ],
    "high_opacity": true,
    "rationale": "key absent from prior publication",
    "priority": 0,
    "row_count_visible": true
   },
   {
    "key": "ofac:47120",
    "source": "ofac_sdn",
    "change_type": "added",
    "name": "PUBLICHNOE AKTSIONERNOE OBSHCHESTVO VOLNA HOLDING",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [],
    "field_changes": [],
    "event_type": "new_designation",
    "authorities": [
     "US/OFAC Russia-Ukraine"
    ],
    "jurisdictions": [
     "RU"
    ],
    "jurisdiction_names": [
     "Russia"
    ],
    "high_opacity": true,
    "rationale": "key absent from prior publication",
    "priority": 0,
    "row_count_visible": true
   },
   {
    "key": "ofac:31877",
    "source": "ofac_sdn",
    "change_type": "removed",
    "name": "Siarhei Ivanavich Karpenka",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [],
    "field_changes": [],
    "event_type": "delisting",
    "authorities": [
     "US/OFAC Belarus"
    ],
    "jurisdictions": [
     "BY"
    ],
    "jurisdiction_names": [
     "Belarus"
    ],
    "high_opacity": true,
    "rationale": "key present in prior publication, absent now",
    "priority": 1,
    "row_count_visible": true
   },
   {
    "key": "ofac:28810",
    "source": "ofac_sdn",
    "change_type": "modified",
    "name": "AKTSIONERNOE OBSHCHESTVO SEVASTOPOL MARINE ENGINEERING",
    "confidence": "high",
    "screening_relevant": false,
    "changed_fields": [
     "programs"
    ],
    "field_changes": [
     {
      "field": "programs",
      "added": [
       "RUSSIA-EO14024"
      ],
      "dropped": [
       "UKRAINE-EO13662"
      ]
     }
    ],
    "event_type": "re_designation",
    "authorities": [
     "US/OFAC Russia-Ukraine"
    ],
    "jurisdictions": [
     "RU",
     "UA"
    ],
    "jurisdiction_names": [
     "Russia",
     "Ukraine"
    ],
    "high_opacity": true,
    "rationale": "programme list changed; legal basis for the restriction has moved",
    "priority": 2,
    "row_count_visible": false
   },
   {
    "key": "ofac:19004",
    "source": "ofac_sdn",
    "change_type": "modified",
    "name": "OBSHCHESTVO S OGRANICHENNOI OTVETSTVENNOSTYU TITAN LOGISTIKA",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [
     "identifiers"
    ],
    "field_changes": [
     {
      "field": "identifiers",
      "added": [
       "Registration Number: 1157847123456 (RU)",
       "Tax ID No.: 7802873456 (RU)"
      ],
      "dropped": []
     }
    ],
    "event_type": "identifier_enrichment",
    "authorities": [
     "US/OFAC Russia-Ukraine"
    ],
    "jurisdictions": [
     "RU"
    ],
    "jurisdiction_names": [
     "Russia"
    ],
    "high_opacity": true,
    "rationale": "registration or tax identifiers added; entity is now joinable to a corporate register",
    "priority": 3,
    "row_count_visible": false
   },
   {
    "key": "ofac:22045",
    "source": "ofac_sdn",
    "change_type": "modified",
    "name": "Yevgeniy Petrovich Zhuravlyov",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [
     "aliases"
    ],
    "field_changes": [
     {
      "field": "aliases",
      "added": [
       "Evgenii Juravlev",
       "Yevgeniy Zhuravlyow [weak]"
      ],
      "dropped": []
     }
    ],
    "event_type": "alias_expansion",
    "authorities": [
     "US/OFAC Russia-Ukraine"
    ],
    "jurisdictions": [
     "RU"
    ],
    "jurisdiction_names": [
     "Russia"
    ],
    "high_opacity": true,
    "rationale": "name strings changed; screening recall differs from yesterday",
    "priority": 4,
    "row_count_visible": false
   },
   {
    "key": "ofac:20551",
    "source": "ofac_sdn",
    "change_type": "modified",
    "name": "ZAKRYTOE AKTSIONERNOE OBSHCHESTVO NEVSKY PRIBOR",
    "confidence": "high",
    "screening_relevant": true,
    "changed_fields": [
     "addresses"
    ],
    "field_changes": [
     {
      "field": "addresses",
      "added": [
       "12A Nevsky Prospekt, St. Petersburg, RU"
      ],
      "dropped": [
       "12 Nevsky Prospekt, St. Petersburg, RU"
      ]
     }
    ],
    "event_type": "administrative",
    "authorities": [
     "US/OFAC Russia-Ukraine"
    ],
    "jurisdictions": [
     "RU"
    ],
    "jurisdiction_names": [
     "Russia"
    ],
    "high_opacity": true,
    "rationale": "non-screening fields changed: addresses",
    "priority": 5,
    "row_count_visible": false
   }
  ],
  "list_sizes": {
   "ofac_sdn": {
    "before": 255,
    "after": 255,
    "changed": 6
   },
   "bis_csl": {
    "before": 2,
    "after": 3,
    "changed": 1
   },
   "eu_fsd": {
    "before": 1,
    "after": 2,
    "changed": 1
   }
  },
  "graph": {
   "nodes": [
    {
     "id": "RU-VOLNA-HOLD",
     "name": "PAO Volna Holding",
     "jurisdiction": "RU",
     "country": "Russia",
     "list_keys": [
      "ofac:47120"
     ]
    },
    {
     "id": "RU-VOLNA-MASH",
     "name": "OOO Volna Mashinostroenie",
     "jurisdiction": "RU",
     "country": "Russia",
     "list_keys": []
    },
    {
     "id": "TR-VOLNA-DIS",
     "name": "Volna Dis Ticaret AS",
     "jurisdiction": "TR",
     "country": "Turkiye",
     "list_keys": []
    },
    {
     "id": "CY-AEGEAN",
     "name": "Aegean Meridian Holdings Ltd",
     "jurisdiction": "CY",
     "country": "Cyprus",
     "list_keys": []
    },
    {
     "id": "AE-MERIDIAN",
     "name": "Meridian General Trading FZE",
     "jurisdiction": "AE",
     "country": "United Arab Emirates",
     "list_keys": []
    },
    {
     "id": "KZ-ARAL",
     "name": "Aral Trading LLP",
     "jurisdiction": "KZ",
     "country": "Kazakhstan",
     "list_keys": []
    },
    {
     "id": "RU-SEVER-INST",
     "name": "AO Sever Instrument",
     "jurisdiction": "RU",
     "country": "Russia",
     "list_keys": [
      "bis:fbc2067c2cd33aaa"
     ]
    },
    {
     "id": "KZ-KASPIY",
     "name": "Kaspiy Precision Machining LLP",
     "jurisdiction": "KZ",
     "country": "Kazakhstan",
     "list_keys": [
      "bis:fee27a089fb2be6c"
     ]
    },
    {
     "id": "BY-KARPENKA",
     "name": "Siarhei Karpenka",
     "jurisdiction": "BY",
     "country": "Belarus",
     "list_keys": [
      "ofac:31877"
     ]
    },
    {
     "id": "BY-NEMIGA",
     "name": "OAO Nemiga Optics",
     "jurisdiction": "BY",
     "country": "Belarus",
     "list_keys": [
      "eu:88417"
     ]
    },
    {
     "id": "BY-NEMIGA-TRADE",
     "name": "Nemiga Trade House OOO",
     "jurisdiction": "BY",
     "country": "Belarus",
     "list_keys": []
    },
    {
     "id": "EE-BALTIC-MARINE",
     "name": "Baltic Marine Services OU",
     "jurisdiction": "EE",
     "country": "Estonia",
     "list_keys": [
      "eu:88301"
     ]
    },
    {
     "id": "LV-BALTIC-SUB",
     "name": "Baltic Marine Logistics SIA",
     "jurisdiction": "LV",
     "country": "Latvia",
     "list_keys": []
    },
    {
     "id": "LT-BALTIC-OPS",
     "name": "Baltic Marine Operations UAB",
     "jurisdiction": "LT",
     "country": "Lithuania",
     "list_keys": []
    },
    {
     "id": "RU-TITAN-LOG",
     "name": "OOO Titan Logistika",
     "jurisdiction": "RU",
     "country": "Russia",
     "list_keys": [
      "ofac:19004"
     ]
    }
   ],
   "edges": [
    {
     "owner": "RU-VOLNA-HOLD",
     "owned": "RU-VOLNA-MASH",
     "percent": 75.0,
     "control": [],
     "source": "RU EGRUL",
     "as_of": "2025-11-14"
    },
    {
     "owner": "TR-VOLNA-DIS",
     "owned": "RU-VOLNA-MASH",
     "percent": 5.0,
     "control": [],
     "source": "RU EGRUL",
     "as_of": "2025-11-14"
    },
    {
     "owner": "RU-VOLNA-MASH",
     "owned": "TR-VOLNA-DIS",
     "percent": 60.0,
     "control": [],
     "source": "TR Ticaret Sicili",
     "as_of": "2025-06-30"
    },
    {
     "owner": "RU-VOLNA-HOLD",
     "owned": "CY-AEGEAN",
     "percent": 50.0,
     "control": [],
     "source": "CY Registrar of Companies",
     "as_of": "2024-09-02"
    },
    {
     "owner": "RU-VOLNA-HOLD",
     "owned": "AE-MERIDIAN",
     "percent": 30.0,
     "control": [],
     "source": "AE free zone filing",
     "as_of": "2025-03-18"
    },
    {
     "owner": "RU-SEVER-INST",
     "owned": "AE-MERIDIAN",
     "percent": 20.0,
     "control": [],
     "source": "AE free zone filing",
     "as_of": "2025-03-18"
    },
    {
     "owner": "RU-VOLNA-MASH",
     "owned": "KZ-ARAL",
     "percent": null,
     "control": [],
     "source": "KZ registry - stake not disclosed",
     "as_of": "2024-12-01"
    },
    {
     "owner": "RU-TITAN-LOG",
     "owned": "KZ-ARAL",
     "percent": 15.0,
     "control": [],
     "source": "KZ registry",
     "as_of": "2024-12-01"
    },
    {
     "owner": "RU-SEVER-INST",
     "owned": "KZ-KASPIY",
     "percent": 55.0,
     "control": [],
     "source": "KZ registry",
     "as_of": "2025-08-19"
    },
    {
     "owner": "BY-KARPENKA",
     "owned": "BY-NEMIGA",
     "percent": 80.0,
     "control": [],
     "source": "BY Unified State Register",
     "as_of": "2023-04-11"
    },
    {
     "owner": "BY-NEMIGA",
     "owned": "BY-NEMIGA-TRADE",
     "percent": 100.0,
     "control": [],
     "source": "BY Unified State Register",
     "as_of": "2023-04-11"
    },
    {
     "owner": "EE-BALTIC-MARINE",
     "owned": "LV-BALTIC-SUB",
     "percent": 55.0,
     "control": [],
     "source": "LV Uznemumu registrs",
     "as_of": "2025-02-20"
    },
    {
     "owner": "EE-BALTIC-MARINE",
     "owned": "LT-BALTIC-OPS",
     "percent": 30.0,
     "control": [
      "right-to-appoint-and-remove-directors"
     ],
     "source": "LT Juridiniu asmenu registras",
     "as_of": "2025-02-20"
    }
   ]
  },
  "closures": {
   "before": {
    "ofac_50pct": {
     "iterations": 2,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "restricted",
       "aggregate": 80.0,
       "iteration": 1,
       "owners": [
        [
         "BY-KARPENKA",
         80.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "restricted",
       "aggregate": 100.0,
       "iteration": 2,
       "owners": [
        [
         "BY-NEMIGA",
         100.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-TITAN-LOG": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    },
    "bis_affiliates": {
     "iterations": 2,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "restricted",
       "aggregate": 55.0,
       "iteration": 1,
       "owners": [
        [
         "RU-SEVER-INST",
         55.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "restricted",
       "aggregate": 80.0,
       "iteration": 1,
       "owners": [
        [
         "BY-KARPENKA",
         80.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "restricted",
       "aggregate": 100.0,
       "iteration": 2,
       "owners": [
        [
         "BY-NEMIGA",
         100.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-TITAN-LOG": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    },
    "eu_ownership_control": {
     "iterations": 1,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "restricted",
       "aggregate": 55.0,
       "iteration": 1,
       "owners": [
        [
         "EE-BALTIC-MARINE",
         55.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "restricted",
       "aggregate": 30.0,
       "iteration": 1,
       "owners": [
        [
         "EE-BALTIC-MARINE",
         30.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": [
        "EE-BALTIC-MARINE"
       ]
      },
      "RU-TITAN-LOG": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    }
   },
   "after": {
    "ofac_50pct": {
     "iterations": 2,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "restricted",
       "aggregate": 75.0,
       "iteration": 1,
       "owners": [
        [
         "RU-VOLNA-HOLD",
         75.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "restricted",
       "aggregate": 60.0,
       "iteration": 2,
       "owners": [
        [
         "RU-VOLNA-MASH",
         60.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "restricted",
       "aggregate": 50.0,
       "iteration": 1,
       "owners": [
        [
         "RU-VOLNA-HOLD",
         50.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "indeterminate",
       "aggregate": 15.0,
       "iteration": 3,
       "owners": [
        [
         "RU-VOLNA-MASH",
         null
        ],
        [
         "RU-TITAN-LOG",
         15.0
        ]
       ],
       "unknown_owners": [
        "RU-VOLNA-MASH"
       ],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-TITAN-LOG": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    },
    "bis_affiliates": {
     "iterations": 2,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "restricted",
       "aggregate": 75.0,
       "iteration": 1,
       "owners": [
        [
         "RU-VOLNA-HOLD",
         75.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "restricted",
       "aggregate": 60.0,
       "iteration": 2,
       "owners": [
        [
         "RU-VOLNA-MASH",
         60.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "restricted",
       "aggregate": 50.0,
       "iteration": 1,
       "owners": [
        [
         "RU-VOLNA-HOLD",
         50.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "restricted",
       "aggregate": 50.0,
       "iteration": 1,
       "owners": [
        [
         "RU-VOLNA-HOLD",
         30.0
        ],
        [
         "RU-SEVER-INST",
         20.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "indeterminate",
       "aggregate": 15.0,
       "iteration": 3,
       "owners": [
        [
         "RU-VOLNA-MASH",
         null
        ],
        [
         "RU-TITAN-LOG",
         15.0
        ]
       ],
       "unknown_owners": [
        "RU-VOLNA-MASH"
       ],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-TITAN-LOG": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    },
    "eu_ownership_control": {
     "iterations": 1,
     "entities": {
      "RU-VOLNA-HOLD": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-VOLNA-MASH": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "TR-VOLNA-DIS": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "CY-AEGEAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "AE-MERIDIAN": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-ARAL": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "RU-SEVER-INST": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "KZ-KASPIY": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-KARPENKA": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "BY-NEMIGA-TRADE": {
       "status": "restricted",
       "aggregate": 100.0,
       "iteration": 1,
       "owners": [
        [
         "BY-NEMIGA",
         100.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "EE-BALTIC-MARINE": {
       "status": "listed",
       "aggregate": 100.0,
       "iteration": 0,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      },
      "LV-BALTIC-SUB": {
       "status": "restricted",
       "aggregate": 55.0,
       "iteration": 1,
       "owners": [
        [
         "EE-BALTIC-MARINE",
         55.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": []
      },
      "LT-BALTIC-OPS": {
       "status": "restricted",
       "aggregate": 30.0,
       "iteration": 1,
       "owners": [
        [
         "EE-BALTIC-MARINE",
         30.0
        ]
       ],
       "unknown_owners": [],
       "control_owners": [
        "EE-BALTIC-MARINE"
       ]
      },
      "RU-TITAN-LOG": {
       "status": "clear",
       "aggregate": 0.0,
       "iteration": null,
       "owners": [],
       "unknown_owners": [],
       "control_owners": []
      }
     }
    }
   }
  },
  "new_derived": {
   "ofac_50pct": [
    "CY-AEGEAN",
    "RU-VOLNA-MASH",
    "TR-VOLNA-DIS"
   ],
   "bis_affiliates": [
    "AE-MERIDIAN",
    "CY-AEGEAN",
    "RU-VOLNA-MASH",
    "TR-VOLNA-DIS"
   ],
   "eu_ownership_control": [
    "BY-NEMIGA-TRADE"
   ]
  },
  "released": {
   "ofac_50pct": [
    "BY-NEMIGA",
    "BY-NEMIGA-TRADE"
   ],
   "bis_affiliates": [
    "BY-NEMIGA",
    "BY-NEMIGA-TRADE"
   ],
   "eu_ownership_control": []
  },
  "divergent": {
   "AE-MERIDIAN": {
    "ofac_50pct": "clear",
    "bis_affiliates": "restricted",
    "eu_ownership_control": "clear"
   },
   "BY-NEMIGA": {
    "ofac_50pct": "clear",
    "bis_affiliates": "clear",
    "eu_ownership_control": "listed"
   },
   "BY-NEMIGA-TRADE": {
    "ofac_50pct": "clear",
    "bis_affiliates": "clear",
    "eu_ownership_control": "restricted"
   },
   "CY-AEGEAN": {
    "ofac_50pct": "restricted",
    "bis_affiliates": "restricted",
    "eu_ownership_control": "clear"
   },
   "EE-BALTIC-MARINE": {
    "ofac_50pct": "clear",
    "bis_affiliates": "clear",
    "eu_ownership_control": "listed"
   },
   "KZ-ARAL": {
    "ofac_50pct": "indeterminate",
    "bis_affiliates": "indeterminate",
    "eu_ownership_control": "clear"
   },
   "KZ-KASPIY": {
    "ofac_50pct": "clear",
    "bis_affiliates": "listed",
    "eu_ownership_control": "clear"
   },
   "LT-BALTIC-OPS": {
    "ofac_50pct": "clear",
    "bis_affiliates": "clear",
    "eu_ownership_control": "restricted"
   },
   "LV-BALTIC-SUB": {
    "ofac_50pct": "clear",
    "bis_affiliates": "clear",
    "eu_ownership_control": "restricted"
   },
   "RU-SEVER-INST": {
    "ofac_50pct": "clear",
    "bis_affiliates": "listed",
    "eu_ownership_control": "clear"
   },
   "RU-TITAN-LOG": {
    "ofac_50pct": "listed",
    "bis_affiliates": "listed",
    "eu_ownership_control": "clear"
   },
   "RU-VOLNA-HOLD": {
    "ofac_50pct": "listed",
    "bis_affiliates": "listed",
    "eu_ownership_control": "clear"
   },
   "RU-VOLNA-MASH": {
    "ofac_50pct": "restricted",
    "bis_affiliates": "restricted",
    "eu_ownership_control": "clear"
   },
   "TR-VOLNA-DIS": {
    "ofac_50pct": "restricted",
    "bis_affiliates": "restricted",
    "eu_ownership_control": "clear"
   }
  },
  "qa": [
   {
    "check": "declared_count",
    "severity": "ok",
    "message": "ofac_sdn: parsed 255 entries, matching the publisher's declared count",
    "detail": {}
   },
   {
    "check": "publication_advanced",
    "severity": "ok",
    "message": "ofac_sdn: publication advanced 08/03/2026 -> 08/04/2026",
    "detail": {}
   },
   {
    "check": "churn_ceiling",
    "severity": "ok",
    "message": "ofac_sdn: 2.35% of entries changed, within the 5% ceiling",
    "detail": {
     "changed": 6,
     "baseline": 255,
     "churn": 0.0235
    }
   },
   {
    "check": "removal_plausibility",
    "severity": "ok",
    "message": "ofac_sdn: 1 removals, within plausible range",
    "detail": {
     "removals": 1,
     "key_stability": "stable"
    }
   },
   {
    "check": "graph_coverage",
    "severity": "warn",
    "message": "6/260 listed parties have a node in the ownership graph; 254 have no computable ownership tail",
    "detail": {
     "listed": 260,
     "covered": 6,
     "orphans": [
      "bis:ac0b2d24e88ad2d3",
      "ofac:20551",
      "ofac:22045",
      "ofac:28810",
      "ofac:60000",
      "ofac:60001",
      "ofac:60002",
      "ofac:60003",
      "ofac:60004",
      "ofac:60005",
      "ofac:60006",
      "ofac:60007",
      "ofac:60008",
      "ofac:60009",
      "ofac:60010",
      "ofac:60011",
      "ofac:60012",
      "ofac:60013",
      "ofac:60014",
      "ofac:60015"
     ],
     "orphan_count": 254
    }
   },
   {
    "check": "unknown_percent_share",
    "severity": "ok",
    "message": "1/13 ownership edges (7.7%) carry no percentage and cannot support a threshold test; derived findings on those paths are indeterminate, not clear",
    "detail": {
     "edges": 13,
     "unknown": 1,
     "share": 0.0769
    }
   },
   {
    "check": "declared_count",
    "severity": "ok",
    "message": "bis_csl: publisher declares no record count; skipped",
    "detail": {}
   },
   {
    "check": "publication_advanced",
    "severity": "ok",
    "message": "bis_csl: publication advanced 2026-08-03 -> 2026-08-04",
    "detail": {}
   },
   {
    "check": "churn_ceiling",
    "severity": "ok",
    "message": "bis_csl: 1 of 2 entries changed; list is below the 100-entry floor where a churn ratio is meaningful, so the proportional test is not applied",
    "detail": {
     "changed": 1,
     "baseline": 2,
     "churn": 0.5
    }
   },
   {
    "check": "removal_plausibility",
    "severity": "ok",
    "message": "bis_csl: 0 removals, within plausible range",
    "detail": {
     "removals": 0,
     "key_stability": "composed"
    }
   },
   {
    "check": "declared_count",
    "severity": "ok",
    "message": "eu_fsd: parsed 2 entries, matching the publisher's declared count",
    "detail": {}
   },
   {
    "check": "publication_advanced",
    "severity": "ok",
    "message": "eu_fsd: publication advanced 2026-08-03 -> 2026-08-04",
    "detail": {}
   },
   {
    "check": "churn_ceiling",
    "severity": "ok",
    "message": "eu_fsd: 1 of 1 entries changed; list is below the 100-entry floor where a churn ratio is meaningful, so the proportional test is not applied",
    "detail": {
     "changed": 1,
     "baseline": 1,
     "churn": 1.0
    }
   },
   {
    "check": "removal_plausibility",
    "severity": "ok",
    "message": "eu_fsd: 0 removals, within plausible range",
    "detail": {
     "removals": 0,
     "key_stability": "unstable"
    }
   }
  ],
  "watch": [
   {
    "watch_id": "bis_affiliates_reimposition",
    "title": "BIS Affiliates Rule reimposed",
    "scheduled_date": "2026-11-10",
    "days_remaining": 98,
    "status": "imminent",
    "date_may_have_moved": true,
    "why_it_matters": "Entity List and MEU licence requirements extend to entities 50% or more owned in aggregate by listed parties. Affiliates are not themselves listed, so the Consolidated Screening List stops being a sufficient screening input on this date.",
    "relevant_documents": [
     {
      "document_number": "2026-14882",
      "title": "Implementation of Additional Sanctions Against Russia: Additions to the Entity List",
      "doc_type": "Rule",
      "publication_date": "2026-08-04",
      "effective_on": "2026-08-04",
      "agencies": [
       "Industry and Security Bureau"
      ],
      "cfr_parts": [
       "15 CFR 744"
      ],
      "docket_ids": [
       "BIS-2026-0031"
      ],
      "abstract": "The Bureau of Industry and Security adds one entity to the Entity List under the destination of Kazakhstan for acting contrary to the national security or foreign policy interests of the United States.",
      "html_url": "https://www.federalregister.gov/documents/2026/08/04/2026-14882"
     },
     {
      "document_number": "2026-14903",
      "title": "Expansion of End-User Controls for Affiliates of Certain Listed Entities: Request for Comment on Scope and Implementation",
      "doc_type": "Proposed Rule",
      "publication_date": "2026-08-04",
      "effective_on": "",
      "agencies": [
       "Industry and Security Bureau"
      ],
      "cfr_parts": [
       "15 CFR 734",
       "15 CFR 744"
      ],
      "docket_ids": [
       "BIS-2025-0044"
      ],
      "abstract": "The Bureau of Industry and Security seeks public comment on the scope of the 50 percent affiliates rule scheduled to take effect on November 10, 2026, including whether the aggregation standard should be modified and whether additional transition relief is warranted.",
      "html_url": "https://www.federalregister.gov/documents/2026/08/04/2026-14903"
     }
    ]
   }
  ]
 },
 "live": {
  "sources": {
   "ofac_sdn": {
    "entries": 19202,
    "declared": 19202,
    "publish_date": "08/18/2026",
    "entity_types": [
     [
      "entity",
      9855
     ],
     [
      "individual",
      7481
     ],
     [
      "vessel",
      1524
     ],
     [
      "aircraft",
      342
     ]
    ],
    "top_programs": [
     [
      "RUSSIA-EO14024",
      6349
     ],
     [
      "SDGT",
      3249
     ],
     [
      "IFSR",
      1545
     ],
     [
      "SDNTK",
      1365
     ],
     [
      "NPWMD",
      1173
     ],
     [
      "IRAN-EO13902",
      914
     ],
     [
      "GLOMAG",
      739
     ],
     [
      "ILLICIT-DRUGS-EO14059",
      704
     ],
     [
      "IRAN",
      674
     ],
     [
      "UKRAINE-EO13662",
      536
     ]
    ],
    "top_countries": [
     [
      "RU",
      "Russia",
      5306
     ],
     [
      "IR",
      "Iran",
      1719
     ],
     [
      "MX",
      "Mexico",
      1187
     ],
     [
      "CN",
      "China",
      1164
     ],
     [
      "AE",
      "United Arab Emirates",
      741
     ],
     [
      "LB",
      "Lebanon",
      400
     ],
     [
      "TR",
      "Turkiye",
      377
     ],
     [
      "CO",
      "Colombia",
      372
     ],
     [
      "SY",
      "Syria",
      353
     ],
     [
      "KP",
      "North Korea",
      331
     ]
    ],
    "organisations": 9855,
    "with_register_id": 7070,
    "aliases": 24576
   },
   "eu_fsd": {
    "entries": 6234,
    "declared": 6234,
    "publish_date": "2026-08-05T16:47:04.449+02:00",
    "entity_types": [
     [
      "individual",
      4462
     ],
     [
      "entity",
      1772
     ]
    ],
    "top_programs": [
     [
      "UKR",
      2960
     ],
     [
      "IRN",
      707
     ],
     [
      "SYR",
      380
     ],
     [
      "BLR",
      374
     ],
     [
      "TAQA",
      337
     ],
     [
      "PRK",
      255
     ],
     [
      "HR",
      170
     ],
     [
      "AFG",
      140
     ],
     [
      "MMR",
      128
     ],
     [
      "COD",
      86
     ]
    ],
    "top_countries": [
     [
      "RU",
      "Russia",
      825
     ],
     [
      "IR",
      "Iran",
      277
     ],
     [
      "SY",
      "Syria",
      101
     ],
     [
      "KP",
      "North Korea",
      95
     ],
     [
      "BY",
      "Belarus",
      91
     ],
     [
      "UA",
      "Ukraine",
      49
     ],
     [
      "CN",
      "China",
      42
     ],
     [
      "AE",
      "United Arab Emirates",
      41
     ],
     [
      "PK",
      "Pakistan",
      40
     ],
     [
      "AF",
      "Afghanistan",
      34
     ]
    ],
    "organisations": 1772,
    "with_register_id": 824,
    "aliases": 24598
   },
   "bis_csl": {
    "entries": 5308,
    "declared": null,
    "publish_date": "",
    "entity_types": [
     [
      "not-published",
      5308
     ]
    ],
    "top_programs": [
     [
      "Entity List (EL)",
      3420
     ],
     [
      "Denied Persons List (DPL)",
      1596
     ],
     [
      "Unverified List (UVL)",
      222
     ],
     [
      "FR 77 FR 61249 No. 195",
      154
     ],
     [
      "FR 89 FR 96837",
      137
     ],
     [
      "FR 89 FR 68548",
      111
     ],
     [
      "FR 87 FR 20299; 87 FR 34136",
      93
     ],
     [
      "FR 89 FR 14388",
      93
     ],
     [
      "FR 87 FR 13141",
      85
     ],
     [
      "FR 88 FR 12158",
      76
     ]
    ],
    "top_countries": [
     [
      "CN",
      "China",
      1340
     ],
     [
      "RU",
      "Russia",
      1132
     ],
     [
      "US",
      "United States",
      963
     ],
     [
      "AE",
      "United Arab Emirates",
      309
     ],
     [
      "HK",
      "Hong Kong",
      262
     ],
     [
      "PK",
      "Pakistan",
      202
     ],
     [
      "IR",
      "Iran",
      147
     ],
     [
      "TR",
      "Turkiye",
      129
     ],
     [
      "GB",
      "United Kingdom",
      103
     ],
     [
      "SG",
      "Singapore",
      75
     ]
    ],
    "organisations": 5308,
    "with_register_id": 0,
    "aliases": 5214
   }
  },
  "as_of": "2026-08-19"
 },
 "failed_run": {
  "date": "2026-08-18",
  "checks": [
   {
    "check": "fetch",
    "severity": "fail",
    "message": "ofac_sdn: could not be retrieved, so this run says nothing about it. retrieved but did not parse: OFAC SDN XML parsed to zero entries",
    "detail": {
     "error": "retrieved but did not parse: OFAC SDN XML parsed to zero entries"
    }
   },
   {
    "check": "fetch",
    "severity": "ok",
    "message": "bis_csl: retrieved from https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json",
    "detail": {
     "origin": "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json"
    }
   },
   {
    "check": "declared_count",
    "severity": "ok",
    "message": "bis_csl: publisher declares no record count; skipped",
    "detail": {}
   },
   {
    "check": "publication_advanced",
    "severity": "ok",
    "message": "bis_csl: no publication date exposed; skipped",
    "detail": {}
   },
   {
    "check": "churn_ceiling",
    "severity": "ok",
    "message": "bis_csl: 5311 of 3 entries changed; list is below the 100-entry floor where a churn ratio is meaningful, so the proportional test is not applied",
    "detail": {
     "changed": 5311,
     "baseline": 3,
     "churn": 1770.3333
    }
   },
   {
    "check": "removal_plausibility",
    "severity": "warn",
    "message": "bis_csl: 3 apparent removals from a source whose identifiers are not stable across publications; these need review before being reported as delistings",
    "detail": {
     "removals": 3,
     "key_stability": "unstable"
    }
   },
   {
    "check": "fetch",
    "severity": "ok",
    "message": "eu_fsd: retrieved from https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content",
    "detail": {
     "origin": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
    }
   },
   {
    "check": "declared_count",
    "severity": "ok",
    "message": "eu_fsd: parsed 6234 entries, matching the publisher's declared count",
    "detail": {}
   },
   {
    "check": "publication_advanced",
    "severity": "ok",
    "message": "eu_fsd: publication advanced 2026-08-04 -> 2026-08-05T16:47:04.449+02:00",
    "detail": {}
   },
   {
    "check": "churn_ceiling",
    "severity": "ok",
    "message": "eu_fsd: 6236 of 2 entries changed; list is below the 100-entry floor where a churn ratio is meaningful, so the proportional test is not applied",
    "detail": {
     "changed": 6236,
     "baseline": 2,
     "churn": 3118.0
    }
   },
   {
    "check": "removal_plausibility",
    "severity": "warn",
    "message": "eu_fsd: 2 apparent removals from a source whose identifiers are not stable across publications; these need review before being reported as delistings",
    "detail": {
     "removals": 2,
     "key_stability": "unstable"
    }
   },
   {
    "check": "fetch",
    "severity": "ok",
    "message": "federal_register: retrieved from https://www.federalregister.gov/api/v1/documents.json",
    "detail": {
     "origin": "https://www.federalregister.gov/api/v1/documents.json"
    }
   }
  ],
  "would_have_reported": {
   "new_designation": 11542,
   "delisting": 5
  }
 }
};
