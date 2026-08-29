local table_index = 0

local citations = {
  ["https://arxiv.org/abs/2310.02304"] = "zelikman2023stop",
  ["https://arxiv.org/abs/2410.04444"] = "yin2024godel",
  ["https://arxiv.org/abs/2504.15228"] = "robeyns2025sica",
  ["https://arxiv.org/abs/2505.22954"] = "zhang2025dgm",
  ["https://arxiv.org/abs/2510.21614"] = "wang2025hgm",
  ["https://arxiv.org/abs/2303.11366"] = "shinn2023reflexion",
  ["https://arxiv.org/abs/2407.01502"] = "kapoor2024agents",
  ["https://arxiv.org/abs/2512.06710"] = "mustahsan2025stochasticity",
  ["https://arxiv.org/abs/2606.08106"] = "shawn2026pace",
  ["https://arxiv.org/abs/2605.12978"] = "zhang2026faulty",
  ["https://arxiv.org/abs/2606.03083"] = "tan2026deltamem",
}

local tables = {
[[
\begin{table*}[t]
\caption*{\textbf{Contribution status.} Systematic measurement is separated from selected trace audits and proposed endpoints.}
\centering\scriptsize
\begin{tabularx}{\textwidth}{@{}p{0.13\textwidth}p{0.20\textwidth}X X@{}}
\toprule
\textbf{Proposition} & \textbf{Status} & \textbf{Recorded evidence} & \textbf{Boundary}\\
\midrule
Retention & Systematically exercised & Immutable state generations and receipts for all three lineages & Persistent change only\\
Expression & Systematically measured & Frozen adapter emissions and held-out semantic-unit coverage & Actor-visible availability only\\
Behavioral mediation & Descriptive summaries plus three selected trace audits & Model/tool/token summaries and complete-chain cases & No general causal mediation effect; complete traces gated\\
Task improvement & Systematically measured & 57 configuration-task outcomes and nine family-level contrasts & One lineage per configuration; descriptive intervals\\
Recursive improvement & Proposed external endpoint & Descendant productivity specified as the operationalization & Not measured\\
\bottomrule
\end{tabularx}
\end{table*}
]],
[[
\begin{table*}[t]
\caption*{\textbf{Control ladder.} Payload controls 3--6 are alternatives rather than a monotonic sequence.}
\centering\scriptsize
\begin{tabularx}{\textwidth}{@{}p{0.15\textwidth}X X@{}}
\toprule
\textbf{Control} & \textbf{Intervention and held-fixed variables} & \textbf{Licensed inference}\\
\midrule
1. Cold floor & Same model, task, harness, and budget; no lineage & Model-and-harness floor\\
2. State-hidden ablation & Same developed lineage and evaluation stack; learned state hidden; a distinct actor-visible channel is required & Effect of enabling retained state only when that distinct channel is verified\\
3. Opaque byte-size sham & Seeded opaque text; report byte ratio and token load & Sensitivity to opaque payload of recorded size\\
4. Token-matched neutral sham & Match tokenizer, position, and count with a preregistered corpus and blinded relevance screen & Payload effect after equalizing first-call token load\\
5. Semantic sham & Plausible units from disjoint task families under blinded relevance screening & Sensitivity to screened-unrelated guidance\\
6. Structure-preserving sham & Preserve count, schema, and token budget while permuting content or metadata & Sensitivity to retained structure apart from its original mapping\\
7. Equivalent duplicates & Byte-identical initial request, model, seed field, task image, harness, and budgets; later trajectories may diverge & Observed within-task execution dispersion\\
8. Native-interface ablation & Hold state, task, model, and budgets fixed while toggling native execution & Effect of the native execution path with recorded downstream changes\\
\bottomrule
\end{tabularx}
\end{table*}
]],
[[
\begin{table*}[t]
\caption{Frozen held-out outcomes. Binary-family intervals are nominal descriptive task-resampling intervals; ActiveGraph has only three tasks, so its intervals are not displayed. The sham columns are descriptive because token load was unmatched and Hybrid also had a byte mismatch.}
\label{tab:outcomes}
\centering\tiny
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}llrrrrr@{}}
\toprule
\textbf{Family} & \textbf{Configuration} & \textbf{Evolved} & \textbf{Labeled no-context draw} & \textbf{Evolved--draw [interval]} & \textbf{Sham} & \textbf{Evolved--sham}\\
\midrule
SWE (10) & Workspace & 8/10 & 8/10 & 0/10 [0, 0] pp & 6/10 & +2/10\\
 & Minimal & 7/10 & 6/10 & +1/10 [-20, +40] pp & 7/10 & 0/10\\
 & Hybrid & 8/10 & 7/10 & +1/10 [0, +30] pp & 8/10 & 0/10\\
Terminal (6) & Workspace & 5/6 & 4/6 & +1/6 [0, +50] pp & 3/6 & +2/6\\
 & Minimal & 3/6 & 5/6 & -2/6 [-66.7, 0] pp & 4/6 & -1/6\\
 & Hybrid & 4/6 & 4/6 & 0/6 [0, 0] pp & 4/6 & 0/6\\
ActiveGraph (3) & Workspace & 82.7\% & 100.0\% & -17.3; interval not shown & 96.0\% & -13.3 pp\\
 & Minimal & 96.7\% & 88.0\% & +8.7; interval not shown & 100.0\% & -3.3 pp\\
 & Hybrid & 82.7\% & 92.7\% & -10.0; interval not shown & 82.7\% & 0.0 pp\\
\bottomrule
\end{tabular}
\end{table*}
]],
[[
\begin{table}[t]
\caption{Retained state after 28 development tasks.}
\label{tab:retention}
\centering\scriptsize
\begin{tabularx}{\columnwidth}{@{}lrrX@{}}
\toprule
 & \multicolumn{2}{c}{\textbf{Accepted after}} & \\
\cmidrule(lr){2-3}
\textbf{Substrate} & \textbf{Passed task} & \textbf{Failed task} & \textbf{Final retained product}\\
\midrule
Workspace & 13 & 12 & 429,731-byte workspace\\
Minimal & 13 & 0 & 13 procedures, 0 capabilities, 28 receipts\\
Hybrid & 15 & 10 & 25 lessons; 62,506-byte Pack\\
\bottomrule
\end{tabularx}
\end{table}
]],
[[
\begin{table*}[t]
\caption{Expression profile. Coverage ratios are within-substrate and do not compare useful information. Workspace counts a bounded partial-file prefix once and reports completeness separately.}
\label{tab:expression}
\centering\tiny
\setlength{\tabcolsep}{3pt}
\begin{tabularx}{\textwidth}{@{}lrrXXX@{}}
\toprule
\textbf{Substrate} & \textbf{Storage} & \textbf{Eligible} & \textbf{Semantic: task; union} & \textbf{Selection; expansion} & \textbf{Execution: automatic; handles}\\
\midrule
Workspace & 14.9\% & 25.9\% & 18/85 (21.2\%); 18/85 & static; 0 pp & none; 0, retained tools hidden\\
Minimal & 1.35\% & 99.6\% & 41/41 (100\%); 41/41 & static; 0 pp & none; N/A, 0 executable units\\
Hybrid & 4.0\% mean & 17.1\% mean & 3/25 (12\%); 17/25 (68\%) & task-conditioned; 56 pp turnover & automatic Pack query; 0 handles\\
\bottomrule
\end{tabularx}
\end{table*}
]],
[[
\begin{table*}[t]
\caption{Equivalent duplicate-execution dispersion and planning diagnostics. Neither planning quantity is a decision threshold.}
\label{tab:duplicates}
\centering\scriptsize
\begin{tabular}{@{}lrrrrr@{}}
\toprule
\textbf{Family} & \textbf{Tasks} & \textbf{Tasks variable across six labels} & \textbf{ICC(1,1)} & \textbf{Maximum pair gap} & \textbf{Continuous-approx. planning}\\
\midrule
SWE & 10 & 3 & 0.72 & 2/10 (20.0 pp) & 30.7 pp\\
Terminal & 6 & 2 & 0.66 & 1/6 (16.7 pp) & 45.1 pp\\
ActiveGraph & 3 & 2 & 0.31, unstable & 21.3 pp & 28.7 pp\\
\bottomrule
\end{tabular}
\end{table*}
]],
[[
\begin{table}[!ht]
\caption{Timeout and adjudication taxonomy.}
\label{tab:timeouts}
\centering\tiny
\begin{tabularx}{\columnwidth}{@{}p{0.18\columnwidth}r p{0.19\columnwidth}X@{}}
\toprule
\textbf{Category} & \textbf{Count} & \textbf{Treatment} & \textbf{Interpretation}\\
\midrule
Official SWE task timeout & 6 & Scored zero & Official evaluation exceeded the frozen 3,600-second task limit.\\
Terminal agent-budget timeout & 6 & Scored zero & Agent exhausted 1,800 seconds and the completed verifier returned zero.\\
ActiveGraph snapshot regrade & 1 & Hash-identical grader-only retry & Original grader contradicted a receipt-bound parsable submission; no model action was rerun.\\
\bottomrule
\end{tabularx}
\end{table}
]],
[[
\begin{table}[!ht]
\caption{Cross-model coding consistency. Sol generated the proposals it coded; undefined kappa indicates zero marginal variance.}
\label{tab:coding-agreement}
\centering\tiny
\setlength{\tabcolsep}{2pt}
\begin{tabularx}{\columnwidth}{@{}Xrrr@{}}
\toprule
\textbf{Field} & \shortstack{\textbf{Exact}\\\textbf{agreement}} & \shortstack{\textbf{Cohen's}\\\textbf{kappa}} & \shortstack{\textbf{Gwet's}\\\textbf{AC1}}\\
\midrule
Primary update target & 76/84 (90.5\%) & 0.000 & 0.904\\
Secondary update target & 47/84 (56.0\%) & -0.081 & 0.543\\
Representational form & 84/84 (100\%) & undefined & 1.000\\
Transfer scope & 63/84 (75.0\%) & 0.470 & 0.717\\
Abstraction level & 59/84 (70.2\%) & 0.529 & 0.647\\
Evidence grounding & 59/84 (70.2\%) & 0.428 & 0.669\\
Failure specificity & 83/84 (98.8\%) & 0.661 & 0.988\\
Validation strategy & 82/84 (97.6\%) & 0.592 & 0.976\\
Consolidation operation & 84/84 (100\%) & undefined & 1.000\\
Executable status & 84/84 (100\%) & undefined & 1.000\\
Anticipated activation & 84/84 (100\%) & undefined & 1.000\\
Counterfactual actionability & 84/84 (100\%) & undefined & 1.000\\
Novelty relative to prior state & 84/84 (100\%) & undefined & 1.000\\
Confidence & 63/84 (75.0\%) & 0.393 & 0.687\\
\bottomrule
\end{tabularx}
\end{table}
]]
}

function Link(el)
  local key = citations[el.target]
  if key == nil then
    if not el.target:match("^https?://") then
      return pandoc.RawInline("latex", "\\path{" .. el.target .. "}")
    end
    return nil
  end
  local cite = pandoc.Cite(
    {},
    {pandoc.Citation(key, "NormalCitation", "", "", 0, 0)}
  )
  local output = {}
  for _, inline in ipairs(el.content) do
    table.insert(output, inline)
  end
  table.insert(output, pandoc.Space())
  table.insert(output, cite)
  return output
end

function Header(el)
  local text = pandoc.utils.stringify(el.content)
  if text == "When Self-Modification Becomes Memory"
      or text == "An Audited Comparison of Three Retention-Interface Configurations Under a Shared Reflection Layer"
      or text == "Minimal appendix" then
    return {}
  end
  if text == "Abstract" then
    return pandoc.RawBlock("latex", "\\begin{abstract}")
  end
  if text == "1. Introduction" then
    return {
      pandoc.RawBlock("latex", "\\end{abstract}"),
      pandoc.Header(1, {pandoc.Str("Introduction")}, el.attr),
    }
  end
  local main_number, main_title = text:match("^(%d+)%.%s+(.+)$")
  if main_number ~= nil then
    if main_number == "9" then
      return {
        pandoc.RawBlock("latex", "\\FloatBarrier"),
        pandoc.Header(1, {pandoc.Str(main_title)}, el.attr),
      }
    end
    if main_number == "10" then
      return {
        pandoc.RawBlock("latex", "\\clearpage"),
        pandoc.Header(1, {pandoc.Str(main_title)}, el.attr),
      }
    end
    return pandoc.Header(1, {pandoc.Str(main_title)}, el.attr)
  end
  local subsection, subsection_title = text:match("^(%d+%.%d+)%s+(.+)$")
  if subsection ~= nil then
    return pandoc.Header(2, {pandoc.Str(subsection_title)}, el.attr)
  end
  local appendix_letter, appendix_title = text:match("^([A-F])%.%s+(.+)$")
  if appendix_letter ~= nil then
    return pandoc.Header(1, {pandoc.Str(appendix_title)}, el.attr)
  end
  return el
end

function Table(el)
  table_index = table_index + 1
  if tables[table_index] == nil then
    error("unexpected table index " .. table_index)
  end
  return pandoc.RawBlock("latex", tables[table_index])
end

function Image(el)
  local name = el.src:match("([^/]+)%.svg$")
  if name ~= nil then
    el.src = "figures/pdf/" .. name .. ".pdf"
  end
  return el
end

function Figure(el)
  local path = nil
  pandoc.walk_block(
    pandoc.Div(el.content),
    {
      Image = function(image)
        path = image.src
        return image
      end
    }
  )
  if path == nil then
    return el
  end
  return pandoc.RawBlock("ourofig", path)
end

function Pandoc(doc)
  local output = {}
  local index = 1
  while index <= #doc.blocks do
    local block = doc.blocks[index]
    if block.t == "BlockQuote"
        and pandoc.utils.stringify(block):match("^Frozen readable companion") then
      index = index + 1
    elseif block.t == "Header" and block.identifier == "artifact-and-appendix-pointers" then
      table.insert(output, pandoc.RawBlock(
        "latex",
        "\\paragraph{Artifact availability.} " ..
        "The compact release can regenerate the manuscript, figures, tables, " ..
        "control sensitivities, audits, and manifest from included data. It " ..
        "supports inspection of the adjudication and frozen coding artifacts. " ..
        "Complete trajectories and trace-dependent case reproduction remain " ..
        "gated pending disclosure review and deposit; the DOI is pending. " ..
        "Unexercised control-ladder rungs and descendant productivity are " ..
        "proposed methods, not empirical outputs of this study."
      ))
      if index < #doc.blocks and doc.blocks[index + 1].t == "BulletList" then
        index = index + 2
      else
        index = index + 1
      end
    elseif block.t == "RawBlock" and block.format == "ourofig" and index < #doc.blocks then
      local path = block.text
      local caption_block = doc.blocks[index + 1]
      if caption_block.t == "Para" then
        local rendered = pandoc.write(
          pandoc.Pandoc({pandoc.Para(caption_block.content)}),
          "latex"
        ):gsub("%s+$", "")
        rendered = rendered:gsub("\\textbf{Figure %d+:%s*", "\\textbf{")
        local figure_number = path:match("figure%-(%d)")
        local widths = {
          ["1"] = "0.82\\textwidth",
          ["2"] = "0.85\\textwidth",
          ["3"] = "0.92\\textwidth",
          ["4"] = "0.85\\textwidth",
          ["5"] = "0.85\\textwidth",
        }
        local width = widths[figure_number] or "0.80\\textwidth"
        table.insert(output, pandoc.RawBlock("latex",
          "\\begin{figure*}[!t]\n\\centering\n" ..
          "\\includegraphics[width=" .. width .. "]{" .. path .. "}\n" ..
          "\\caption{" .. rendered .. "}\n" ..
          "\\label{fig:" .. figure_number .. "}\n\\end{figure*}"
        ))
        index = index + 2
      else
        table.insert(output, block)
        index = index + 1
      end
    else
      table.insert(output, block)
      index = index + 1
    end
  end
  doc.blocks = output
  return doc
end
