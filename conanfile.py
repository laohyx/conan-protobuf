from conans import ConanFile, CMake, tools, ConfigureEnvironment
import os
import shutil


class ProtobufConan(ConanFile):
    name = "Protobuf"
    version = "3.1.0"
    url = "https://github.com/sunsided/conan-protobuf.git"
    license = "https://github.com/google/protobuf/blob/v3.1.0/LICENSE"
    requires = "zlib/1.2.8@lasote/stable"
    settings = "os", "compiler", "build_type", "arch"
    exports = "CMakeLists.txt", "lib*.cmake", "extract_includes.bat.in", "protoc.cmake", "tests.cmake", "change_dylib_names.sh", "protobuf-cpp-3.1.0.zip"
    options = {"shared": [True, False]}
    default_options = "shared=True"
    generators = "cmake"

    def config(self):
        self.options["zlib"].shared = self.options.shared

    def source(self):
        tools.unzip("protobuf-cpp-3.1.0.zip")
        os.unlink("protobuf-cpp-3.1.0.zip")

    def build(self):
        if self.settings.os == "Windows":
            args = ['-DBUILD_TESTING=OFF']
            args += ['-DBUILD_SHARED_LIBS=%s' % ('ON' if self.options.shared else 'OFF')]
            cmake = CMake(self.settings)
            self.run('cd protobuf-3.1.0/cmake && cmake . %s %s' % (cmake.command_line, ' '.join(args)))
            self.run("cd protobuf-3.1.0/cmake && cmake --build . %s" % cmake.build_config)
        else:
            env = ConfigureEnvironment(self.deps_cpp_info, self.settings)

            concurrency = 1
            try:
                import multiprocessing
                concurrency = multiprocessing.cpu_count()
            except (ImportError, NotImplementedError):
                pass

            self.run("chmod +x protobuf-3.1.0/autogen.sh")
            self.run("chmod +x protobuf-3.1.0/configure")
            self.run("cd protobuf-3.1.0 && ./autogen.sh")

            args = []
            if not self.options.shared:
                args += ['--disable-shared']

            self.run("cd protobuf-3.1.0 && %s ./configure %s" % (env.command_line, ' '.join(args)))
            self.run("cd protobuf-3.1.0 && make -j %s" % concurrency)

    def package(self):
        self.copy_headers("*.h", "protobuf-3.1.0/src")

        if self.settings.os == "Windows":
            self.copy("*.lib", "lib", "protobuf-3.1.0/cmake", keep_path=False)
            self.copy("protoc.exe", "bin", "protobuf-3.1.0/cmake/%s" % self.settings.build_type, keep_path=False)

            if self.options.shared:
                self.copy("*.dll", "bin", "protobuf-3.1.0/cmake/%s" % self.settings.build_type, keep_path=False)
        else:
            # Copy the libs to lib
            if not self.options.shared:
                self.copy("*.a", "lib", "protobuf-3.1.0/src/.libs", keep_path=False)
            else:
                self.copy("*.so*", "lib", "protobuf-3.1.0/src/.libs", keep_path=False)
                self.copy("*.9.dylib", "lib", "protobuf-3.1.0/src/.libs", keep_path=False)

            # Copy the exe to bin
            if self.settings.os == "Macos":
                if not self.options.shared:
                    self.copy("protoc", "bin", "protobuf-3.1.0/src/", keep_path=False)
                else:
                    # "protoc" has libproto*.dylib dependencies with absolute file paths.
                    # Change them to be relative.
                    self.run("cd protobuf-3.1.0/src/.libs && bash ../../cmake/change_dylib_names.sh")

                    # "src/protoc" may be a wrapper shell script which execute "src/.libs/protoc".
                    # Copy "src/.libs/protoc" instead of "src/protoc"
                    self.copy("protoc", "bin", "protobuf-3.1.0/src/.libs/", keep_path=False)
                    self.copy("*.9.dylib", "bin", "protobuf-3.1.0/src/.libs", keep_path=False)
            else:
                self.copy("protoc", "bin", "protobuf-3.1.0/src/", keep_path=False)

    def package_info(self):
        basename = "libprotobuf"
        if self.settings.build_type == "Debug":
            basename = "libprotobufd"

        if self.settings.os == "Windows":
            self.cpp_info.libs = [basename]
            if self.options.shared:
                self.cpp_info.defines = ["PROTOBUF_USE_DLLS"]
        elif self.settings.os == "Macos":
            self.cpp_info.libs = [basename + ".a"] if not self.options.shared else [basename + ".9.dylib"]
        else:
            self.cpp_info.libs = [basename + ".a"] if not self.options.shared else [basename + ".so.9"]
