using System;
using System.Text.RegularExpressions;
using System.Reflection;
using System.Collections.Generic;
using System.IO;
using Parser.Lib;
using TI.Declarator.ParserCommon;
using System.Linq;
using Smart.Parser.Lib;

namespace Smart.Parser.Adapters
{
    public class BigramsHolder
    {
        static Dictionary<string, double> Bigrams = ReadBigrams();

        static Dictionary<string, double> ReadBigrams()
        {
            var currentAssembly = Assembly.GetExecutingAssembly();
            var result = new Dictionary<string, double>();
            using (var stream = currentAssembly.GetManifestResourceStream("Smart.Parser.Lib.Resources.bigrams.txt"))
            {
                using (var reader = new StreamReader(stream))
                {
                    while (reader.Peek() >= 0)
                    {
                        var line = reader.ReadLine();
                        var parts = line.Split('\t');
                        double mutual_information = double.Parse(parts[1]);
                        if (mutual_information > 0)
                        {
                            result[parts[0]] = mutual_information;
                        }
                    }
                }
            }
            return result;
        }

        static List<string> TokenizeCellText(string text)
        {
            List<string> result = new List<string>();
            foreach (var token in text.Split())
            {
                token.Trim(
                    '﻿', ' ', // two different spaces
                    '\n', '\r',
                    ',', '!', '.', '{', '}',
                    '[', ']', '(', ')',
                    '"', '«', '»', '\'');
                if (token.Length > 0) result.Add(token);
            }
            return result;
        }


        public static bool CheckMergeRow(List<string> row1, List<string> row2)
        {
            if (row1.Count != row2.Count)
            {
                return false;
            }
            for (int i = 0; i < row1.Count; ++i)
            {
                var tokens1 = TokenizeCellText(row1[i]);
                var tokens2 = TokenizeCellText(row2[i]);
                if (tokens1.Count > 0 && tokens2.Count > 0)
                {
                    string lastWord = tokens1.Last();
                    string firstWord = tokens2.First();
                    if (lastWord.Length > 0 && firstWord.Length > 0)
                    {
                        string joinExplanation = "";
                        if (Bigrams.ContainsKey(lastWord + " " + firstWord))
                        {
                            joinExplanation = "frequent bigram";
                        }

                        if (Regex.Matches(lastWord, @".+\p{Pd}$").Count > 0
                              && Char.IsLower(firstWord[0])
                           )
                        {
                            joinExplanation = "word break regexp";
                        }

                        if (tokens1.Count + tokens2.Count == 3
                            && TextHelpers.CanBePatronymic(tokens2[tokens2.Count - 1])
                            && !tokens2[tokens2.Count - 1].Contains('.')
                            && Char.IsUpper(tokens1[0][0])
                            )
                        {
                            joinExplanation = "person regexp";
                        }

                        if (TextHelpers.MayContainsRole(string.Join(" ", tokens1))
                            && TextHelpers.CanBePatronymic(tokens2.Last())
                            && Char.IsUpper(tokens2[0][0])
                            && tokens1.All(x => !TextHelpers.CanBePatronymic(x))
                        )
                        {
                            joinExplanation = "role and person regexp";
                        }

                        if (Regex.Match(string.Join(" ", tokens1), @".+\([^\)]+", RegexOptions.Singleline).Success && 
                            Regex.Match(string.Join(" ", tokens2), @"^[^\(]+\).*", RegexOptions.Singleline).Success)
                        {
                            joinExplanation = "non-closed ) regexp";
                        }

                        if (firstWord.TrimStart()[0] == '(')
                        {
                            joinExplanation = "open ( regexp";
                        }
                        
                        if (joinExplanation != "")
                        {
                            Logger.Debug(string.Format(
                                "Join rows using {0} on cells \"{1}\" and \"{2}\"",
                                joinExplanation,
                                row1[i].ReplaceEolnWithSpace(),
                                row2[i].ReplaceEolnWithSpace()));
                            return true;

                        }
                    }
                }
            }
            return false;
        }


    }
}