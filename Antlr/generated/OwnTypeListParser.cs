//------------------------------------------------------------------------------
// <auto-generated>
//     This code was generated by a tool.
//     ANTLR Version: 4.8
//
//     Changes to this file may cause incorrect behavior and will be lost if
//     the code is regenerated.
// </auto-generated>
//------------------------------------------------------------------------------

// Generated from C:\tmp\smart_parser\smart_parser\Antlr\src\OwnTypeListParser.g4 by ANTLR 4.8

// Unreachable code detected
#pragma warning disable 0162
// The variable '...' is assigned but its value is never used
#pragma warning disable 0219
// Missing XML comment for publicly visible type or member '...'
#pragma warning disable 1591
// Ambiguous reference in cref attribute
#pragma warning disable 419

using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections.Generic;
using Antlr4.Runtime;
using Antlr4.Runtime.Atn;
using Antlr4.Runtime.Misc;
using Antlr4.Runtime.Tree;
using DFA = Antlr4.Runtime.Dfa.DFA;

[System.CodeDom.Compiler.GeneratedCode("ANTLR", "4.8")]
[System.CLSCompliant(false)]
public partial class OwnTypeListParser : Parser {
	protected static DFA[] decisionToDFA;
	protected static PredictionContextCache sharedContextCache = new PredictionContextCache();
	public const int
		SQUARE_METER=1, HECTARE=2, OT=3, NUMBER=4, REALTY_ID=5, FRACTION_ASCII=6, 
		DOLYA_WORD=7, SEMICOLON=8, COMMA=9, OPN_BRK=10, CLS_BRK=11, SPC=12, FRACTION_UNICODE=13, 
		HYPHEN=14, OWN_TYPE=15, COUNTRY=16, REALTY_TYPE=17;
	public const int
		RULE_own_type_list = 0, RULE_own_type = 1;
	public static readonly string[] ruleNames = {
		"own_type_list", "own_type"
	};

	private static readonly string[] _LiteralNames = {
		null, null, "'\u0433\u0430'", "'\u043E\u0442'", null, null, null, null, 
		"';'", "','", "'('", "')'", null, null, "'-'"
	};
	private static readonly string[] _SymbolicNames = {
		null, "SQUARE_METER", "HECTARE", "OT", "NUMBER", "REALTY_ID", "FRACTION_ASCII", 
		"DOLYA_WORD", "SEMICOLON", "COMMA", "OPN_BRK", "CLS_BRK", "SPC", "FRACTION_UNICODE", 
		"HYPHEN", "OWN_TYPE", "COUNTRY", "REALTY_TYPE"
	};
	public static readonly IVocabulary DefaultVocabulary = new Vocabulary(_LiteralNames, _SymbolicNames);

	[NotNull]
	public override IVocabulary Vocabulary
	{
		get
		{
			return DefaultVocabulary;
		}
	}

	public override string GrammarFileName { get { return "OwnTypeListParser.g4"; } }

	public override string[] RuleNames { get { return ruleNames; } }

	public override string SerializedAtn { get { return new string(_serializedATN); } }

	static OwnTypeListParser() {
		decisionToDFA = new DFA[_ATN.NumberOfDecisions];
		for (int i = 0; i < _ATN.NumberOfDecisions; i++) {
			decisionToDFA[i] = new DFA(_ATN.GetDecisionState(i), i);
		}
	}

		public OwnTypeListParser(ITokenStream input) : this(input, Console.Out, Console.Error) { }

		public OwnTypeListParser(ITokenStream input, TextWriter output, TextWriter errorOutput)
		: base(input, output, errorOutput)
	{
		Interpreter = new ParserATNSimulator(this, _ATN, decisionToDFA, sharedContextCache);
	}

	public partial class Own_type_listContext : ParserRuleContext {
		public Own_typeContext[] own_type() {
			return GetRuleContexts<Own_typeContext>();
		}
		public Own_typeContext own_type(int i) {
			return GetRuleContext<Own_typeContext>(i);
		}
		public Own_type_listContext(ParserRuleContext parent, int invokingState)
			: base(parent, invokingState)
		{
		}
		public override int RuleIndex { get { return RULE_own_type_list; } }
		public override void EnterRule(IParseTreeListener listener) {
			IOwnTypeListParserListener typedListener = listener as IOwnTypeListParserListener;
			if (typedListener != null) typedListener.EnterOwn_type_list(this);
		}
		public override void ExitRule(IParseTreeListener listener) {
			IOwnTypeListParserListener typedListener = listener as IOwnTypeListParserListener;
			if (typedListener != null) typedListener.ExitOwn_type_list(this);
		}
		public override TResult Accept<TResult>(IParseTreeVisitor<TResult> visitor) {
			IOwnTypeListParserVisitor<TResult> typedVisitor = visitor as IOwnTypeListParserVisitor<TResult>;
			if (typedVisitor != null) return typedVisitor.VisitOwn_type_list(this);
			else return visitor.VisitChildren(this);
		}
	}

	[RuleVersion(0)]
	public Own_type_listContext own_type_list() {
		Own_type_listContext _localctx = new Own_type_listContext(Context, State);
		EnterRule(_localctx, 0, RULE_own_type_list);
		int _la;
		try {
			EnterOuterAlt(_localctx, 1);
			{
			State = 5;
			ErrorHandler.Sync(this);
			_la = TokenStream.LA(1);
			do {
				{
				{
				State = 4; own_type();
				}
				}
				State = 7;
				ErrorHandler.Sync(this);
				_la = TokenStream.LA(1);
			} while ( _la==OWN_TYPE );
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			ErrorHandler.ReportError(this, re);
			ErrorHandler.Recover(this, re);
		}
		finally {
			ExitRule();
		}
		return _localctx;
	}

	public partial class Own_typeContext : ParserRuleContext {
		public ITerminalNode OWN_TYPE() { return GetToken(OwnTypeListParser.OWN_TYPE, 0); }
		public ITerminalNode COMMA() { return GetToken(OwnTypeListParser.COMMA, 0); }
		public Own_typeContext(ParserRuleContext parent, int invokingState)
			: base(parent, invokingState)
		{
		}
		public override int RuleIndex { get { return RULE_own_type; } }
		public override void EnterRule(IParseTreeListener listener) {
			IOwnTypeListParserListener typedListener = listener as IOwnTypeListParserListener;
			if (typedListener != null) typedListener.EnterOwn_type(this);
		}
		public override void ExitRule(IParseTreeListener listener) {
			IOwnTypeListParserListener typedListener = listener as IOwnTypeListParserListener;
			if (typedListener != null) typedListener.ExitOwn_type(this);
		}
		public override TResult Accept<TResult>(IParseTreeVisitor<TResult> visitor) {
			IOwnTypeListParserVisitor<TResult> typedVisitor = visitor as IOwnTypeListParserVisitor<TResult>;
			if (typedVisitor != null) return typedVisitor.VisitOwn_type(this);
			else return visitor.VisitChildren(this);
		}
	}

	[RuleVersion(0)]
	public Own_typeContext own_type() {
		Own_typeContext _localctx = new Own_typeContext(Context, State);
		EnterRule(_localctx, 2, RULE_own_type);
		int _la;
		try {
			EnterOuterAlt(_localctx, 1);
			{
			{
			State = 9; Match(OWN_TYPE);
			State = 11;
			ErrorHandler.Sync(this);
			_la = TokenStream.LA(1);
			if (_la==COMMA) {
				{
				State = 10; Match(COMMA);
				}
			}

			}
			}
		}
		catch (RecognitionException re) {
			_localctx.exception = re;
			ErrorHandler.ReportError(this, re);
			ErrorHandler.Recover(this, re);
		}
		finally {
			ExitRule();
		}
		return _localctx;
	}

	private static char[] _serializedATN = {
		'\x3', '\x608B', '\xA72A', '\x8133', '\xB9ED', '\x417C', '\x3BE7', '\x7786', 
		'\x5964', '\x3', '\x13', '\x10', '\x4', '\x2', '\t', '\x2', '\x4', '\x3', 
		'\t', '\x3', '\x3', '\x2', '\x6', '\x2', '\b', '\n', '\x2', '\r', '\x2', 
		'\xE', '\x2', '\t', '\x3', '\x3', '\x3', '\x3', '\x5', '\x3', '\xE', '\n', 
		'\x3', '\x3', '\x3', '\x2', '\x2', '\x4', '\x2', '\x4', '\x2', '\x2', 
		'\x2', '\xF', '\x2', '\a', '\x3', '\x2', '\x2', '\x2', '\x4', '\v', '\x3', 
		'\x2', '\x2', '\x2', '\x6', '\b', '\x5', '\x4', '\x3', '\x2', '\a', '\x6', 
		'\x3', '\x2', '\x2', '\x2', '\b', '\t', '\x3', '\x2', '\x2', '\x2', '\t', 
		'\a', '\x3', '\x2', '\x2', '\x2', '\t', '\n', '\x3', '\x2', '\x2', '\x2', 
		'\n', '\x3', '\x3', '\x2', '\x2', '\x2', '\v', '\r', '\a', '\x11', '\x2', 
		'\x2', '\f', '\xE', '\a', '\v', '\x2', '\x2', '\r', '\f', '\x3', '\x2', 
		'\x2', '\x2', '\r', '\xE', '\x3', '\x2', '\x2', '\x2', '\xE', '\x5', '\x3', 
		'\x2', '\x2', '\x2', '\x4', '\t', '\r',
	};

	public static readonly ATN _ATN =
		new ATNDeserializer().Deserialize(_serializedATN);


}
