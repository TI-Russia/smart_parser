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

using Antlr4.Runtime.Misc;
using IParseTreeListener = Antlr4.Runtime.Tree.IParseTreeListener;
using IToken = Antlr4.Runtime.IToken;

/// <summary>
/// This interface defines a complete listener for a parse tree produced by
/// <see cref="OwnTypeListParser"/>.
/// </summary>
[System.CodeDom.Compiler.GeneratedCode("ANTLR", "4.8")]
[System.CLSCompliant(false)]
public interface IOwnTypeListParserListener : IParseTreeListener {
	/// <summary>
	/// Enter a parse tree produced by <see cref="OwnTypeListParser.own_type_list"/>.
	/// </summary>
	/// <param name="context">The parse tree.</param>
	void EnterOwn_type_list([NotNull] OwnTypeListParser.Own_type_listContext context);
	/// <summary>
	/// Exit a parse tree produced by <see cref="OwnTypeListParser.own_type_list"/>.
	/// </summary>
	/// <param name="context">The parse tree.</param>
	void ExitOwn_type_list([NotNull] OwnTypeListParser.Own_type_listContext context);
	/// <summary>
	/// Enter a parse tree produced by <see cref="OwnTypeListParser.own_type"/>.
	/// </summary>
	/// <param name="context">The parse tree.</param>
	void EnterOwn_type([NotNull] OwnTypeListParser.Own_typeContext context);
	/// <summary>
	/// Exit a parse tree produced by <see cref="OwnTypeListParser.own_type"/>.
	/// </summary>
	/// <param name="context">The parse tree.</param>
	void ExitOwn_type([NotNull] OwnTypeListParser.Own_typeContext context);
}
