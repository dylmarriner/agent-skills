// managed_probe — ask a managed vendor assembly questions about itself, in-process, on
// Linux. Built for reversing obfuscated .NET tools: the obfuscator's own routines only
// run inside the process that loaded the assembly, so we load it and call it.
//
//   types     <asm> [substring]            list types whose name contains substring
//   find      <asm> <RetType> <P1,P2,...>  static methods with this exact signature
//   ctor      <asm> <TypeFullName> <P1,...>  construct an internal type
//   invoke    <asm> <TypeFullName> <method> [arg...]   static call; Stream result -> file
//   resources <asm> <outdir>               dump every manifest resource
//   strings   <asm> <tokens.txt> <out.tsv> invoke the obfuscator's String::Decrypt(int)
//
// Type and method names in an obfuscated assembly are often non-printable characters,
// so match by SIGNATURE. The real members are `internal`, hence BindingFlags.NonPublic
// everywhere. Sibling DLLs are resolved from MANAGED_APP_DIR (the installed product
// directory) because an assembly loaded from bytes has no .deps.json of its own.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;

class Program {
    static Assembly Asm;
    static string[] Argv;

    static Type[] SafeTypes(Assembly a) {
        try { return a.GetTypes(); }
        catch (ReflectionTypeLoadException e) { return e.Types.Where(t => t != null).ToArray(); }
    }

    // An assembly loaded from bytes cannot resolve its siblings by name. Point the
    // load context at the installed product directory.
    static void RegisterProbe() {
        var dir = Environment.GetEnvironmentVariable("MANAGED_APP_DIR");
        if (string.IsNullOrEmpty(dir)) {
            Console.Error.WriteLine("warning: MANAGED_APP_DIR unset; sibling assemblies will not resolve");
            return;
        }
        AssemblyLoadContext.Default.Resolving += (ctx, name) => {
            var p = Path.Combine(dir, name.Name + ".dll");
            return File.Exists(p) ? ctx.LoadFromAssemblyPath(p) : null;
        };
    }

    // A type name may be a vendor type or a framework type; try the target assembly
    // first, then the runtime. Framework names (System.IO.Stream, System.Xml.Linq.*)
    // are what the interesting signatures are made of.
    static Type Resolve(string name, bool required = true) {
        var t = (Asm == null ? null : SafeTypes(Asm).FirstOrDefault(x => x.FullName == name))
                ?? Type.GetType(name)
                ?? AppDomain.CurrentDomain.GetAssemblies().Select(x => x.GetType(name)).FirstOrDefault(x => x != null);
        if (t == null && required) throw new Exception("type not found: " + name);
        return t;
    }

    // Accept a type name, or `void`, or a builtin shim name (string, int, bool, byte).
    static Type ResolveArg(string name) => name switch {
        "void" => typeof(void),
        "string" => typeof(string),
        "int" => typeof(int),
        "uint" => typeof(uint),
        "long" => typeof(long),
        "bool" => typeof(bool),
        "byte" => typeof(byte),
        "bytes" => typeof(byte[]),
        _ => Resolve(name)
    };

    static Type[] ResolveList(string csv) =>
        string.IsNullOrEmpty(csv) ? Type.EmptyTypes : csv.Split(',').Select(ResolveArg).ToArray();

    static object Coerce(Type t, string s) {
        if (t == typeof(string)) return s;
        if (t == typeof(byte[])) return s.Length == 0 ? Array.Empty<byte>() : Enumerable.Range(0, s.Length / 2)
            .Select(i => Convert.ToByte(s.Substring(i * 2, 2), 16)).ToArray();
        if (t == typeof(Stream)) return File.OpenRead(s);
        if (t.IsEnum) return Enum.Parse(t, s);
        return Convert.ChangeType(s, t);
    }

    static int Emit(object r) {
        switch (r) {
            case null: Console.WriteLine("null"); return 0;
            case Stream s: {
                var outp = Argv.Length > 0 ? Argv[Argv.Length - 1] : "out.bin";
                using var fs = File.Create(outp);
                s.CopyTo(fs);
                Console.Error.WriteLine($"wrote {outp} ({new FileInfo(outp).Length} bytes)");
                return 0;
            }
            case byte[] b: Console.WriteLine(string.Join(" ", b.Select(x => x.ToString("X2")))); return 0;
            case System.Collections.IEnumerable en when !(r is string):
                foreach (var x in en) Console.WriteLine(x?.ToString()); return 0;
            default: Console.WriteLine(r.ToString()); return 0;
        }
    }

    static int Strings(string asmPath, string tokenPath, string outPath) {
        var asm = Assembly.Load(File.ReadAllBytes(asmPath));
        var tokens = File.ReadAllLines(tokenPath).Select(s => s.Trim())
            .Where(s => s.Length > 0).Select(int.Parse).ToList();

        // The literal decoder: any static method (string) <- (int).
        MethodInfo found = null;
        foreach (var t in SafeTypes(asm))
            foreach (var m in t.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)) {
                var ps = m.GetParameters();
                if (m.ReturnType == typeof(string) && ps.Length == 1 && ps[0].ParameterType == typeof(int)) { found = m; break; }
                if (found != null) break;
            }
        if (found == null) { Console.Error.WriteLine("string decoder not found"); return 2; }
        Console.Error.WriteLine($"decoder: {found.DeclaringType.FullName}.{found.Name}");

        var sb = new StringBuilder();
        foreach (var tk in tokens) {
            string v;
            try { v = (string)found.Invoke(null, new object[] { tk }); }
            catch (Exception ex) { var e = ex; while (e.InnerException != null) e = e.InnerException; v = "<ERR " + e.GetType().Name + ": " + e.Message + ">"; }
            sb.Append(tk).Append('\t').Append(v is null ? "<null>" : v.Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t")).Append('\n');
        }
        File.WriteAllText(outPath, sb.ToString());
        Console.Error.WriteLine($"wrote {outPath} ({tokens.Count} tokens)");
        return 0;
    }

    static int Resources(string asmPath, string outDir) {
        var asm = Assembly.Load(File.ReadAllBytes(asmPath));
        Directory.CreateDirectory(outDir);
        foreach (var n in asm.GetManifestResourceNames()) {
            using var s = asm.GetManifestResourceStream(n);
            var safe = new string(n.Select(c => Path.GetInvalidFileNameChars().Contains(c) ? '_' : c).ToArray());
            using var fs = File.Create(Path.Combine(outDir, safe));
            s.CopyTo(fs);
            Console.WriteLine($"{n}\t{s.Length}");
        }
        return 0;
    }

    static int Main(string[] a) {
        if (a.Length < 2) { Console.Error.WriteLine("usage: managed_probe types|find|ctor|invoke|resources|strings ..."); return 1; }
        Argv = a;
        try {
            RegisterProbe();
            var mode = a[0];
            if (mode == "strings") return Strings(a[1], a[2], a[3]);
            if (mode == "resources") return Resources(a[1], a[2]);

            Asm = Assembly.Load(File.ReadAllBytes(a[1]));
            switch (mode) {
                case "types":
                    foreach (var t in SafeTypes(Asm))
                        if (a.Length < 3 || t.FullName.Contains(a[2]))
                            Console.WriteLine(t.FullName);
                    return 0;
                case "find": {
                    var ret = ResolveArg(a[2]); var args = ResolveList(a[3]);
                    foreach (var t in SafeTypes(Asm))
                        foreach (var m in t.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)) {
                            if (m.ReturnType != ret) continue;
                            var ps = m.GetParameters();
                            if (ps.Length != args.Length) continue;
                            var ok = true;
                            for (int i = 0; i < args.Length; i++) if (ps[i].ParameterType != args[i]) ok = false;
                            if (ok) Console.WriteLine($"{t.FullName} :: {m.ReturnType.Name} {m.Name}({string.Join(",", ps.Select(p => p.ParameterType.Name))})");
                        }
                    return 0;
                }
                case "ctor": {
                    var t = Resolve(a[2]);
                    var args = ResolveList(a.Length > 3 ? a[3] : "");
                    var c = t.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                             .FirstOrDefault(x => { var ps = x.GetParameters(); return ps.Length == args.Length && ps.Select(p => p.ParameterType).SequenceEqual(args); });
                    if (c == null) { Console.Error.WriteLine("no matching constructor"); return 2; }
                    var vals = new object[args.Length];
                    for (int i = 0; i < args.Length; i++) vals[i] = Coerce(args[i], a[4 + i]);
                    return Emit(c.Invoke(vals));
                }
                case "invoke": {
                    var t = Resolve(a[2]);
                    foreach (var m in t.GetMethods(BindingFlags.Static | BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)) {
                        if (m.Name != a[3]) continue;
                        var ps = m.GetParameters();
                        if (ps.Length != a.Length - 4) continue;
                        var vals = new object[ps.Length];
                        for (int i = 0; i < ps.Length; i++) vals[i] = Coerce(ps[i].ParameterType, a[4 + i]);
                        return Emit(m.Invoke(m.IsStatic ? null : Activator.CreateInstance(t), vals));
                    }
                    Console.Error.WriteLine("no matching method"); return 2;
                }
                default: return 1;
            }
        } catch (Exception ex) {
            var e = ex; while (e.InnerException != null) e = e.InnerException;
            Console.Error.WriteLine("FATAL " + e.GetType().Name + ": " + e.Message);
            return 1;
        }
    }
}
